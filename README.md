# Automatic Safeway and Jewel-Osco coupon clipper

[![Build](https://img.shields.io/github/checks-status/johnmyrda/safeway-coupons/main?label=build)][gh-actions]

**safeway-coupons** signs in to Safeway or Jewel-Osco, finds available
loyalty offers, and clips offers that are not already associated with the
account.

## How it works

1. Headless Chromium signs in and obtains the authenticated retailer session.
2. The retailer's offers API is used to retrieve and clip coupons.
3. Results are printed for each configured account.

The retailer may require a one-time code sent by SMS or email. The runner keeps
an interactive terminal available for this prompt. CAPTCHA challenges are not
supported.

## Setup

The supported workflow uses Podman and the included container image. The image
contains Debian Chromium and its matching driver.

```console
podman machine start
podman build -t localhost/safeway-coupons:local .
python3 scripts/configure.py
```

The configuration script prompts for one retailer account and creates the
Git-ignored `accounts` file. To configure multiple accounts or retailers, edit
that file and add one section per account. Safeway is the default when
`retailer` is omitted.

```ini
[safeway-account]
retailer = safeway
username = shared.account@example.com
password = safeway-password

[jewel-account]
retailer = jewel-osco
username = shared.account@example.com
password = jewel-password
```

For backward compatibility, a section name is used as the username when the
`username` option is omitted.

## Running

Start with a dry run. With no arguments, the runner signs in and lists what it
would clip without changing any coupons:

```console
sh scripts/run-podman.sh
```

After reviewing the output, clip one coupon as a live test or clip everything:

```console
sh scripts/run-podman.sh --max-clip 1
sh scripts/run-podman.sh --max-clip 0
```

Use email instead of SMS for device verification when needed:

```console
COUPON_VERIFICATION_METHOD=email sh scripts/run-podman.sh
```

Additional application options can be passed through the runner:

```console
sh scripts/run-podman.sh --help
sh scripts/run-podman.sh --dry-run --debug
```

The runner mounts `accounts` read-only, disables result email, and does not
schedule future runs. Debug files are written to the Git-ignored `debug/`
directory and may contain account-specific information.

Stop the Podman machine when it is no longer needed:

```console
podman machine stop
```

## Scheduled runs

A user crontab runs the clipper daily at 3:15 AM local time:

```cron
15 3 * * * /Users/john/git/safeway-coupons/scripts/run-scheduled.sh
```

The scheduler performs a live all-coupon run, starts and stops Podman when
needed, prevents overlapping runs, and keeps private daily logs in `logs/` for
30 days. The Mac must be awake at the scheduled time. Device verification
cannot be completed from cron; if it is requested, inspect the log and run the
clipper interactively.

The scheduler can be tested safely with an explicit dry run:

```console
scripts/run-scheduled.sh --dry-run
```

## Project layout

- `safeway_coupons/session.py` handles browser sign-in and device verification.
- `safeway_coupons/client.py` communicates with the retailer's offers API.
- `safeway_coupons/safeway.py` coordinates offer selection and clipping.
- `safeway_coupons/retailers.py` defines retailer URLs and display names.
- `safeway_coupons/app.py` defines the command-line interface.
- `scripts/configure.py` creates the local account configuration.
- `scripts/run-podman.sh` runs the container with safe local defaults.
- `scripts/run-scheduled.sh` manages unattended cron runs and logging.

## Maintenance

Update dependencies, run checks, and rebuild the image:

```console
uv lock --upgrade
uv sync --locked
uv run --locked poe test
podman build --pull=always --no-cache -t localhost/safeway-coupons:local .
```

## Development

Set up the environment and optional pre-commit hook:

```console
uv sync --locked
uv run --locked pre-commit install
```

Ruff handles linting and formatting, while ty performs static type checking.
Common commands:

```console
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked ty check safeway_coupons tests
uv run --locked pytest
uv run --locked poe test
uv build
```

[gh-actions]: https://github.com/johnmyrda/safeway-coupons/actions?query=branch%3Amain
