# Automatic Safeway coupon clipper

[![Build](https://img.shields.io/github/checks-status/johnmyrda/safeway-coupons/main?label=build)][gh-actions]
[![GitHub stars](https://img.shields.io/github/stars/johnmyrda/safeway-coupons?style=social)][repo]

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

## Setup and usage with Podman on Apple Silicon

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

[cookie-python]: https://github.com/smkent/cookie-python
[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[gh-actions]: https://github.com/johnmyrda/safeway-coupons/actions?query=branch%3Amain
[uv]: https://docs.astral.sh/uv/getting-started/installation/
[repo]: https://github.com/johnmyrda/safeway-coupons
[requests]: https://requests.readthedocs.io/en/latest/
