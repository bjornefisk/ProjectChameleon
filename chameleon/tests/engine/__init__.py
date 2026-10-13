"""Resolve this test package's ``engine`` name to source engine submodules."""

# ``unittest discover -s tests`` imports this directory as top-level
# ``engine``. Keep the test module discoverable while resolving product
# submodules (``engine.main``, ``engine.errors``, ...) from the source package.
from pathlib import Path

_TEST_PACKAGE = Path(__file__).resolve().parent
_SOURCE_PACKAGE = _TEST_PACKAGE.parents[1] / "engine"
__path__[:] = [str(_SOURCE_PACKAGE), str(_TEST_PACKAGE)]