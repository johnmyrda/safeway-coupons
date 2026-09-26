#!/bin/sh
# Run the coupon clipper from cron, preserving the Podman machine's prior state.
set -u
umask 077

PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
export PATH

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
log_dir="$root/logs"
lock_file="$log_dir/scheduled.lock"
machine=podman-machine-default
started_machine=0

mkdir -p "$log_dir"
chmod 700 "$log_dir"
find "$log_dir" -type f -name 'scheduled-*.log' -mtime +30 -delete
log_file="$log_dir/scheduled-$(date +%Y-%m-%d).log"
exec >>"$log_file" 2>&1

printf '\n[%s] Starting scheduled coupon run\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
if ! /usr/bin/shlock -f "$lock_file" -p $$; then
    echo "Another scheduled coupon run is active; skipping."
    exit 1
fi

cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ "$started_machine" -eq 1 ]; then
        echo "Stopping Podman machine"
        if ! podman machine stop "$machine"; then
            echo "Unable to stop Podman machine" >&2
            [ "$status" -ne 0 ] || status=1
        fi
    fi
    rm -f "$lock_file"
    printf '[%s] Scheduled coupon run finished with status %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$status"
    exit "$status"
}
trap cleanup EXIT HUP INT TERM

state=$(podman machine inspect "$machine" --format '{{.State}}' 2>/dev/null || true)
case "$state" in
    running)
        echo "Podman machine is already running"
        ;;
    stopped)
        echo "Starting Podman machine"
        podman machine start "$machine"
        started_machine=1
        ;;
    *)
        echo "Unable to determine Podman machine state: ${state:-unknown}" >&2
        exit 1
        ;;
esac

cd "$root"
if [ "$#" -eq 0 ]; then
    set -- --max-clip 0
fi
sh scripts/run-podman.sh "$@"
