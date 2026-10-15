"""Bounded process execution primitives for the review evidence capsule."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_limited: bool = False
    reader_error: BaseException | None = None
    capture_incomplete: bool = False


def _process_exited_without_reaping(process: subprocess.Popen) -> bool:
    if os.name != "posix":
        return process.poll() is not None
    waitid = getattr(os, "waitid", None)
    if waitid is None:
        return process.poll() is not None
    try:
        result = waitid(
            os.P_PID,
            process.pid,
            os.WEXITED | os.WNOHANG | os.WNOWAIT,
        )
    except ChildProcessError:
        return process.poll() is not None
    return result is not None and result.si_pid == process.pid


def _terminate_process(process: subprocess.Popen) -> None:
    if getattr(process, "_chameleon_termination_started", False):
        return
    if process.returncode is not None and not (
        os.name == "posix" and getattr(os, "waitid", None) is None
    ):
        return
    setattr(process, "_chameleon_termination_started", True)
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.monotonic() + 5
        while not _process_exited_without_reaping(process):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
    elif process.poll() is None:
        try:
            process.terminate()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass

def execute_process(
    command: Sequence[str],
    cwd: Path,
    timeout: int,
    max_output_bytes: int,
    *,
    env: Mapping[str, str] | None = None,
    stdin_bytes: bytes | None = None,
    merge_stderr: bool = False,
    stdout_path: Path | None = None,
    stdout_fd: int | None = None,
    terminate_on_output_limit: bool = True,
) -> ProcessResult:
    """Run one process with bounded capture, timeout, and process-group cleanup."""
    if stdout_fd is not None and stdout_path is not None:
        raise ValueError("stdout_fd and stdout_path are mutually exclusive")
    if stdout_fd is not None:
        output_file = os.fdopen(os.dup(stdout_fd), "wb")
    elif stdout_path is not None:
        output_file = stdout_path.open("wb")
    else:
        output_file = None
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdin=subprocess.PIPE if stdin_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
            start_new_session=os.name == "posix",
        )
    except OSError:
        if output_file is not None:
            output_file.close()
        raise

    captured = {"stdout": bytearray(), "stderr": bytearray()}
    total = 0
    lock = threading.Lock()
    output_limited = threading.Event()
    reader_errors: list[BaseException] = []
    readers: list[threading.Thread] = []
    writer: threading.Thread | None = None
    try:
        def drain(name: str, stream: object) -> None:
            nonlocal total
            if stream is None:
                return
            try:
                while True:
                    reader = getattr(stream, "read1", stream.read)
                    chunk = reader(65536)  # type: ignore[operator]
                    if not chunk:
                        return
                    with lock:
                        remaining = max_output_bytes - total
                        accepted = chunk[: max(0, remaining)]
                        if accepted:
                            if name == "stdout" and output_file is not None:
                                output_file.write(accepted)
                            else:
                                captured[name].extend(accepted)
                            total += len(accepted)
                        if len(chunk) > remaining:
                            output_limited.set()
                            if terminate_on_output_limit:
                                return
            except (OSError, ValueError) as error:
                reader_errors.append(error)

        streams = [("stdout", process.stdout)]
        if not merge_stderr:
            streams.append(("stderr", process.stderr))
        readers = [
            threading.Thread(target=drain, args=(name, stream), daemon=True)
            for name, stream in streams
        ]
        for reader in readers:
            reader.start()

        if stdin_bytes is not None and process.stdin is not None:
            def write_input() -> None:
                try:
                    process.stdin.write(stdin_bytes)
                    process.stdin.close()
                except (BrokenPipeError, OSError, ValueError):
                    pass

            writer = threading.Thread(target=write_input, daemon=True)
            writer.start()

        deadline = time.monotonic() + timeout
        timed_out = False
        termination_requested = False
        while not _process_exited_without_reaping(process):
            if terminate_on_output_limit and output_limited.is_set():
                _terminate_process(process)
                termination_requested = True
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                _terminate_process(process)
                termination_requested = True
                break
            time.sleep(min(0.05, remaining))
        if not termination_requested:
            _terminate_process(process)
            termination_requested = True

        if writer is not None:
            writer.join(timeout=1)
            if writer.is_alive() and process.stdin is not None:
                process.stdin.close()
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
        for reader in readers:
            reader.join(timeout=1)
        capture_incomplete = any(reader.is_alive() for reader in readers)
        if capture_incomplete and not termination_requested:
            _terminate_process(process)
            termination_requested = True
        if capture_incomplete:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            for reader in readers:
                reader.join(timeout=1)
            capture_incomplete = any(reader.is_alive() for reader in readers)
        if process.stdout is not None and not process.stdout.closed:
            process.stdout.close()
        if process.stderr is not None and not process.stderr.closed:
            process.stderr.close()
        if output_file is not None:
            output_file.flush()
            output_file.close()

        return ProcessResult(
            returncode=process.returncode,
            stdout=bytes(captured["stdout"]),
            stderr=bytes(captured["stderr"]),
            timed_out=timed_out,
            output_limited=output_limited.is_set(),
            reader_error=reader_errors[0] if reader_errors else None,
            capture_incomplete=capture_incomplete,
        )
    except BaseException:
        try:
            _terminate_process(process)
        finally:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            if process.stdout is not None and not process.stdout.closed:
                process.stdout.close()
            if process.stderr is not None and not process.stderr.closed:
                process.stderr.close()
            for reader in readers:
                reader.join(timeout=1)
            if output_file is not None:
                output_file.close()
        raise
