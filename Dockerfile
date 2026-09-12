# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=docker.io/library/python:3.14.7-slim-bookworm
FROM ${PYTHON_IMAGE} AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_CONCURRENT_BUILDS=1
WORKDIR /build
RUN uv venv /opt/venv
# Dependency installation is cached independently of application source edits.
COPY requirements-container.txt ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /opt/venv/bin/python --require-hashes \
        -r requirements-container.txt
COPY pyproject.toml README.md LICENSE ./
COPY safeway_coupons ./safeway_coupons
ARG POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.0"
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /opt/venv/bin/python --no-deps .

FROM ${PYTHON_IMAGE} AS runtime
# Native browser and matching driver; no Intel emulation or external apt key.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates chromium chromium-driver busybox-static tini && \
    rm -rf /var/lib/apt/lists/* && \
    for target in /usr/sbin/sendmail /usr/sbin/crond /usr/bin/crontab; do \
        ln -sf /bin/busybox "$target"; \
    done && \
    mkdir -p /opt/chromedriver /debug && \
    cp /usr/bin/chromedriver /opt/chromedriver/chromedriver

ENV PATH="/opt/venv/bin:$PATH" \
    SAFEWAY_CHROMEDRIVER_PATH="/opt/chromedriver/chromedriver" \
    CRON_SCHEDULE="5 2 * * *" \
    SAFEWAY_ACCOUNTS_FILE="" \
    DEBUG_DIR="/debug" \
    EXTRA_ARGS="" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"
COPY --from=builder /opt/venv /opt/venv
COPY --chmod=755 docker/entrypoint /entrypoint
# Root is retained for the existing BusyBox cron entrypoint. Podman runs
# rootless on the host. One-shot callers override CMD with safeway-coupons.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/entrypoint"]
