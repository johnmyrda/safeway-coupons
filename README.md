# Automatic Safeway coupon clipper

[![PyPI](https://img.shields.io/pypi/v/safeway-coupons)][pypi]
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/safeway-coupons)][pypi]
[![Build](https://img.shields.io/github/checks-status/smkent/safeway-coupons/main?label=build)][gh-actions]
[![codecov](https://codecov.io/gh/smkent/safeway-coupons/branch/main/graph/badge.svg)][codecov]
[![GitHub stars](https://img.shields.io/github/stars/smkent/safeway-coupons?style=social)][repo]

**safeway-coupons** is a script that will log in to an account on safeway.com,
and attempt to select all of the "Safeway for U" electronic coupons on the site
so they don't have to each be clicked manually.

## Design notes

Safeway's sign in page is protected by a web application firewall (WAF).
safeway-coupons performs authentication using a headless instance of Google
Chrome. Authentication may fail based on your IP's reputation, either by
presenting a CAPTCHA or denying sign in attempts altogether. safeway-coupons
currently does not have support for prompting the user to solve CAPTCHAs.

Once a signed in session is established, coupon clipping is performed using HTTP
requests via [requests][requests].

## Installation and usage with Docker

A Docker container is provided which runs safeway-coupons with cron. The cron
schedule and your Safeway account details may be configured using environment
variables, or with an accounts file.

Example `docker-compose.yaml` with configuration via environment variables:

```yaml
version: "3.7"

services:
  safeway-coupons:
    image: ghcr.io/smkent/safeway-coupons:latest
    environment:
      CRON_SCHEDULE: "0 2 * * *"  # Run at 2:00 AM UTC each day
      # TZ: Antarctica/McMurdo  # Optional time zone to use instead of UTC
      SMTPHOST: your.smtp.host
      SAFEWAY_ACCOUNT_USERNAME: your.safeway.account.email@example.com
      SAFEWAY_ACCOUNT_PASSWORD: very_secret
      SAFEWAY_ACCOUNT_MAIL_FROM: your.email@example.com
      SAFEWAY_ACCOUNT_MAIL_TO: your.email@example.com
      # EXTRA_ARGS: --debug  # Optional
    restart: unless-stopped
```

Example `docker-compose.yaml` with configuration via accounts file:

```yaml
version: "3.7"

services:
  safeway-coupons:
    image: ghcr.io/smkent/safeway-coupons:latest
    environment:
      CRON_SCHEDULE: "0 2 * * *"  # Run at 2:00 AM UTC each day
      # TZ: Antarctica/McMurdo  # Optional time zone to use instead of UTC
      SMTPHOST: your.smtp.host
      SAFEWAY_ACCOUNTS_FILE: /accounts_file
      # EXTRA_ARGS: --debug  # Optional
    restart: unless-stopped
    volumes:
      - path/to/safeway_accounts_file:/accounts_file:ro
```

Start the container by running:

```console
docker-compose up -d
```

Debugging information can be viewed in the container log:

```console
docker-compose logs -f
```

## Local setup with Podman (including Apple Silicon)

`Dockerfile` uses native Debian Chromium and its matching driver rather than
emulating Intel Chrome. `Dockerfile.podman` is a compatibility symlink to it.
The multi-stage build uses `uv sync --locked --no-dev` with the same `uv.lock`
as development. uv and build tooling are not copied into the runtime venv.
Dependency layers are cached separately from application source. An allowlisted
`.dockerignore` excludes credentials and debug artifacts from the build context.

```console
podman machine start  # if not already running
podman build --jobs=1 --memory=1280m --memory-swap=1280m -t localhost/safeway-coupons:local .
python3 scripts/configure.py
sh scripts/run-podman.sh                 # dry run: sign in, list, do not clip
sh scripts/run-podman.sh --max-clip 1    # test clipping one coupon
sh scripts/run-podman.sh --max-clip 0    # clip all available coupons
```

Enter credentials in the local terminal, not in chat. The setup script creates
an ignored `accounts` file with mode 0600. It is mounted read-only, not baked into
the image. Debug artifacts are stored in ignored `debug/`; treat them as private.
Email is disabled and no schedule is started by these commands. The target is
still **Safeway**, not Jewel-Osco. Site authentication may still be blocked by a
CAPTCHA or changes to the sign-in page.

### Resource limits and maintenance

On this Mac the Podman VM is configured for 2 CPUs and 2048 MiB guest RAM.
The one-shot runner caps each container at 2 CPUs, 1280 MiB memory (no swap),
256 processes/threads and 256 MiB shared memory. A browser smoke test passes
within these limits; full authenticated runs may need tuning if they hit OOM.
The VM's macOS memory footprint can exceed its guest allocation. Stop it after
use to reclaim memory (this stops any other containers in the VM too):

```console
podman machine stop
```

The runner does not automatically start or stop a shared VM. Restart it with
`podman machine start` before the next run. No scheduled service is enabled.

Refresh Python dependencies intentionally, then rebuild and test:

```console
uv lock --upgrade
uv sync --locked
uv run --locked pytest
```

`uv.lock` is the single lock for development, CI and containers. Python runtime
packages and the Python 3.14.7 base-image version are pinned; Debian browser
packages and isolated Python build dependencies are not fully pinned. Use
`podman build --pull=always --no-cache --jobs=1 --memory=1280m --memory-swap=1280m -t localhost/safeway-coupons:local .`
periodically to pick up base and browser security updates. The runtime retains
root for compatibility with BusyBox cron; the Podman VM uses rootless containers.

## Installation from PyPI

### Prerequisites

* Python 3.14 or newer (development and containers use 3.14.7).
* Google Chrome (for authentication performed via Selenium).
* Optional: `sendmail` (for email support)

### Installation

[safeway-coupons is available on PyPI][pypi]:

```console
uv tool install --python 3.14 safeway-coupons
```

### Usage

For best results, run this program once a day or so with a cron daemon.

For full usage options, run

```console
safeway-coupons --help
```

### Configuration

**safeway-coupons** can clip coupons for one or more Safeway accounts in a
single run, depending on the configuration method used.

If a sender email address is configured, a summary email will be sent for each
Safeway account via `sendmail`. The email recipient defaults to the Safeway
account email address, but can be overridden for each account.

Accounts are searched via the following methods in the listed order. Only one
account configuration method may be used at a time.

#### With environment variables

A single Safeway account can be configured with environment variables:

* `SAFEWAY_ACCOUNT_USERNAME`: Account email address (required)
* `SAFEWAY_ACCOUNT_PASSWORD`: Account password (required)
* `SAFEWAY_ACCOUNT_MAIL_FROM`: Sender address for email summary
* `SAFEWAY_ACCOUNT_MAIL_TO`: Recipient address for email summary

#### With config file

Multiple Safeway accounts can be provided in an ini-style config file, with a
section for each account. For example:

```ini
email_sender = sender@example.com   ; optional

[safeway.account@example.com]       ; required
password = 12345                    ; required
notify = your.email@example.com     ; optional
```

Provide the path to your config file using the `-c` or `--accounts-config`
option:

```console
safeway-coupons -c path/to/config/file
```

## Development

### Setup with [uv][uv]

Install uv 0.12.13 or newer, then run:

```console
uv sync --locked
uv run --locked pre-commit install
```

uv installs the Python version in `.python-version` and creates `.venv` with
runtime and development dependencies. No separate environment activation or
Poetry installation is needed.

### Builds and versions

```console
uv build
```

Hatchling and hatch-vcs build wheels and source distributions with versions
inferred from Git tags (for example, `v1.2.3`). Development checkouts get a
PEP 440 development version. Use a full Git checkout including tags; release CI
fetches full history. Runtime version reporting reads installed package metadata.

Container build contexts deliberately exclude Git history. Local images use
`0.0.0`; release CI passes the Git-derived version with
`--build-arg PROJECT_VERSION=...`. To build a package from source without Git
metadata, explicitly set `SETUPTOOLS_SCM_PRETEND_VERSION`.

To update a dependency, use `uv add` (or `uv add --dev` for development tools).
Commit both `pyproject.toml` and `uv.lock` when dependency declarations change.

### Invocation with docker-compose

safeway-coupons can be executed within a Docker container using
`docker-compose.dev.yaml`.

To use, first create an `accounts` file in the same directory with your
safeway-coupons accounts configuration. Then, execute safeway-coupons within a
container using docker-compose:

```console
docker-compose -f docker-compose.dev.yaml up --build
```

The container will run safeway-coupons once, attempt to clip one coupon, and
then stop.

To change the safeway-coupons arguments, modify the `command` value in
`docker-compose.dev.yaml`.

When finished with development tasks, the docker-compose state can be cleaned up
with:

```console
docker-compose -f docker-compose.dev.yaml down
```

### Development tasks

* Setup: `uv sync --locked`
* Run static checks: `uv run --locked poe lint` or
  `uv run --locked pre-commit run --all-files`
* Run unit tests: `uv run --locked pytest`
* Run static checks and tests: `uv run --locked poe test`
* Build distributions: `uv build`

---

Created from [smkent/cookie-python][cookie-python] using
[cookiecutter][cookiecutter]

[codecov]: https://codecov.io/gh/smkent/safeway-coupons
[cookie-python]: https://github.com/smkent/cookie-python
[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[gh-actions]: https://github.com/smkent/safeway-coupons/actions?query=branch%3Amain
[uv]: https://docs.astral.sh/uv/getting-started/installation/
[pypi]: https://pypi.org/project/safeway-coupons/
[repo]: https://github.com/smkent/safeway-coupons
[requests]: https://requests.readthedocs.io/en/latest/
