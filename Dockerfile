# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=docker.io/library/python:3.14.7-slim-bookworm
FROM ${PYTHON_IMAGE} AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_CONCURRENT_BUILDS=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /build
# One lock for development and production; cache dependencies before source.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY README.md LICENSE ./
COPY safeway_coupons ./safeway_coupons
# Git history is deliberately excluded from the build context. Release CI
# supplies the Git-derived version; local images default to 0.0.0.
ARG PROJECT_VERSION="0.0.0"
RUN --mount=type=cache,target=/root/.cache/uv \
    SETUPTOOLS_SCM_PRETEND_VERSION="$PROJECT_VERSION" \
    uv sync --locked --no-dev --no-editable

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
