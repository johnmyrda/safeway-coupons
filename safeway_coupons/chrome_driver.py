import contextlib
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import undetected_chromedriver as uc  # type: ignore

CHROMEDRIVER_PATH = (
    Path(os.environ["SAFEWAY_CHROMEDRIVER_PATH"])
    if os.environ.get("SAFEWAY_CHROMEDRIVER_PATH")
    else Path.home()
    / ".local"
    / "share"
    / "undetected_chromedriver"
    / "undetected_chromedriver"
)


class ChromeDriverDoesNotExist(Exception):
    pass


@contextlib.contextmanager
def chrome_driver(headless: bool = True) -> Iterator[uc.Chrome]:
    options = uc.ChromeOptions()
    options.headless = headless
    for option in [
        "--incognito",
        "--no-sandbox",
        "--disable-extensions",
        "--disable-application-cache",
        "--disable-gpu",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
    ]:
        options.add_argument(option)
    if headless:
        options.add_argument("--headless=new")
    if os.environ.get("SAFEWAY_CHROMEDRIVER_PATH"):
        driver = uc.Chrome(
            options=options,
            driver_executable_path=str(CHROMEDRIVER_PATH),
        )
    else:
        driver = uc.Chrome(options=options)
    yield driver
    driver.quit()


def chrome_driver_version() -> str:
    if not CHROMEDRIVER_PATH.is_file():
        raise ChromeDriverDoesNotExist(
            f"Error: {CHROMEDRIVER_PATH} does not exist"
        )
    cmd = [str(CHROMEDRIVER_PATH), "--version"]
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True)
    return result.stdout.decode()


def init() -> None:
    with contextlib.suppress(ChromeDriverDoesNotExist):
        print(chrome_driver_version())
        return
    print("Initializing Chrome Driver")
    with chrome_driver() as driver:
        print("Connect to example.com")
        driver.get("https://example.com")
    print(chrome_driver_version())
