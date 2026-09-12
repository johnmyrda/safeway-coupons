#!/bin/sh
# Default to a dry run; pass --max-clip 1 or other CLI options explicitly.
set -eu
cd "$(dirname "$0")/.."
if [ ! -f accounts ]; then
    echo 'Run python3 scripts/configure.py first.' >&2
    exit 1
fi
mkdir -p debug
chmod 700 debug
if [ "$#" -eq 0 ]; then
    set -- --dry-run
fi
# Allocate a terminal only when one is available (needed for verification).
if [ -t 0 ] && [ -t 1 ]; then
    set -- -it "$@"
else
    set -- -i "$@"
fi
terminal_flag=$1
shift
exec podman run "$terminal_flag" --rm --shm-size=256m \
    --cpus=2 --memory=1280m --memory-swap=1280m --pids-limit=256 \
    -e SAFEWAY_VERIFICATION_METHOD="${SAFEWAY_VERIFICATION_METHOD:-sms}" \
    -v "$PWD/accounts:/config/accounts:ro" \
    -v "$PWD/debug:/debug" \
    localhost/safeway-coupons:local \
    safeway-coupons --accounts-config /config/accounts \
    --debug-dir /debug --no-email "$@"
