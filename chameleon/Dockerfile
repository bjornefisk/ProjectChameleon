ARG PYTHON_BASE=python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5
FROM --platform=linux/amd64 ${PYTHON_BASE}
ARG PYTHON_BASE

ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN rm -rf /etc/apt/sources.list.d && mkdir -p /etc/apt/sources.list.d /app/provenance
COPY apt/sources.list /etc/apt/sources.list
COPY apt/packages.lock /app/provenance/apt-packages.lock
COPY apt/packages.sha256 /app/provenance/apt-packages.sha256
COPY apt/snapshot-evidence.json /app/provenance/apt-snapshot-evidence.json
RUN python -c 'import hashlib,json,pathlib,sys; p=pathlib.Path; e=json.load(open(sys.argv[1])); files={"sources.list":p("/etc/apt/sources.list"),"apt-packages.lock":p("/app/provenance/apt-packages.lock"),"apt-packages.sha256":p("/app/provenance/apt-packages.sha256")}; expected={"sources.list":e["sources_file_sha256"],"apt-packages.lock":e["package_lock_sha256"],"apt-packages.sha256":e["package_archive_hashes_sha256"]}; digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest(); bad=[name for name,path in files.items() if digest(path)!=expected[name]]; bad and sys.exit(f"Debian lock input hash mismatch: {bad}")' /app/provenance/apt-snapshot-evidence.json

RUN set -eux; \
    test -s /etc/apt/sources.list; \
    test -z "$(find /etc/apt/sources.list.d -type f -print -quit)"; \
    apt-get -o Dir::Etc::sourcelist=/etc/apt/sources.list \
      -o Dir::Etc::sourceparts=- update; \
    apt-cache -o Dir::Etc::sourcelist=/etc/apt/sources.list \
      -o Dir::Etc::sourceparts=- policy libgl1 libegl1 libglib2.0-0 fontconfig; \
    dpkg-query -W -f='${binary:Package}=${Version}\n' | sort > /tmp/dpkg-before.txt; \
    mkdir -p /tmp/apt-debs/partial; \
    apt-get install -y --no-install-recommends \
      -o Dir::Etc::sourcelist=/etc/apt/sources.list \
      -o Dir::Etc::sourceparts=- \
      -o Dir::Cache::archives=/tmp/apt-debs/ \
      libgl1=1.6.0-1 libegl1=1.6.0-1 \
      libglib2.0-0=2.74.6-2+deb12u9 fontconfig=2.14.1-4; \
    (cd /tmp/apt-debs && sha256sum -c /app/provenance/apt-packages.sha256); \
    dpkg-query -W -f='${binary:Package}=${Version}\n' | sort > /tmp/dpkg-after.txt; \
    grep -v '^#' /app/provenance/apt-packages.lock | sort > /tmp/dpkg-expected-added.txt; \
    comm -13 /tmp/dpkg-before.txt /tmp/dpkg-after.txt > /tmp/dpkg-added.txt; \
    if ! cmp -s /tmp/dpkg-expected-added.txt /tmp/dpkg-added.txt; then \
      echo 'installed Debian package closure differs from apt/packages.lock'; \
      cat /tmp/dpkg-expected-added.txt /tmp/dpkg-added.txt; \
      exit 1; \
    fi; \
    while IFS='=' read -r package version; do \
      package="${package%%:*}"; \
      test -s "/usr/share/doc/${package}/copyright"; \
    done < /tmp/dpkg-after.txt; \
    cp /tmp/dpkg-after.txt /app/provenance/dpkg-query.txt; \
    rm -rf /var/lib/apt/lists/* /tmp/apt-debs /tmp/dpkg-*.txt

COPY requirements.in /app/provenance/python-requirements.in
COPY requirements.lock /app/provenance/python-requirements.lock
COPY renderer-build.in /app/provenance/renderer-build.in
COPY renderer-build.lock /app/provenance/renderer-build.lock
COPY renderer-artifact.json /app/provenance/renderer-artifact.json
COPY .wheelhouse/manifest.json /app/provenance/wheelhouse-manifest.json
COPY .wheelhouse/ /tmp/wheelhouse/
RUN python -c 'import hashlib,json,pathlib,sys; p=pathlib.Path("/app/provenance"); h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest(); m=json.load(open(p/"wheelhouse-manifest.json")); a=json.load(open(p/"renderer-artifact.json")); expected={"requirements.lock":h(p/"python-requirements.lock"),"renderer-build.lock":h(p/"renderer-build.lock"),"renderer-artifact.json":h(p/"renderer-artifact.json")}; m.get("inputs")==expected or sys.exit("wheelhouse manifest input hashes mismatch"); m.get("base_image")==sys.argv[1] and a["build"]["base_image"]==sys.argv[1] or sys.exit("wheelhouse or renderer base image mismatch"); a["build"]["build_requirements_sha256"]==expected["renderer-build.lock"] or sys.exit("renderer build lock hash mismatch"); m.get("target")=="linux/amd64" and m.get("python")==a["build"]["python"] or sys.exit("wheelhouse target mismatch")' "$PYTHON_BASE"

RUN set -eux; \
    python -c 'import hashlib,json,pathlib,sys; m=json.load(open(sys.argv[1])); p=pathlib.Path(sys.argv[2])/m["wheel"]["filename"]; h=hashlib.sha256(p.read_bytes()).hexdigest(); h == m["wheel"]["sha256"] or sys.exit(f"renderer wheel hash mismatch: {h}")' \
      /app/provenance/renderer-artifact.json /tmp/wheelhouse; \
    PIP_CACHE_DIR=/tmp/empty-pip-cache python -m pip install --disable-pip-version-check \
      --force-reinstall --no-cache-dir --no-index --find-links=/tmp/wheelhouse \
      --require-hashes --only-binary=:all: \
      -r /app/provenance/python-requirements.lock; \
    renderer_wheel="$(python -c 'import json; print(json.load(open("/app/provenance/renderer-artifact.json"))["wheel"]["filename"])')"; \
    PIP_CACHE_DIR=/tmp/empty-pip-cache python -m pip install --disable-pip-version-check \
      --no-cache-dir --no-index --no-deps "/tmp/wheelhouse/${renderer_wheel}"; \
    python -c 'import json,sys; from importlib.metadata import distribution; m=json.load(open(sys.argv[1])); d=distribution(m["wheel"]["distribution"]); u=json.loads(d.read_text("direct_url.json")); a=u.get("archive_info",{}); h=a.get("hashes",{}).get("sha256") or a.get("hash","").removeprefix("sha256="); h == m["wheel"]["sha256"] or sys.exit(f"renderer direct_url hash mismatch: {h!r}"); d.version == m["wheel"]["version"] or sys.exit(f"unexpected renderer version: {d.version}")' \
      /app/provenance/renderer-artifact.json; \
    python -c 'import cr_renderer, datasets, jsonschema, PIL, pydantic, skia'; \
    python -m pip inspect --local > /app/provenance/pip-inspect.json; \
    python -m pip freeze --all | sort > /app/provenance/pip-freeze.txt; \
    rm -rf /tmp/wheelhouse /tmp/empty-pip-cache

ENV HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1

COPY chameleon_design_schema_v0.9.json .
COPY brand_kit/ ./brand_kit/
COPY renderer/ ./renderer/
COPY engine/ ./engine/

# input/ and output/ are mounted as volumes at run time; neither is baked in.
RUN mkdir -p /app/input /app/output

ENTRYPOINT ["python", "-m", "engine.main"]
