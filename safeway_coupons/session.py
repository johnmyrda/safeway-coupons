import contextlib
import os
import sys
import json
import time
import urllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Optional

import requests
import selenium.webdriver.support.expected_conditions as ec
import undetected_chromedriver as uc  # type: ignore
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import By
from selenium.webdriver.support.wait import WebDriverWait

from .accounts import Account
from .chrome_driver import chrome_driver
from .errors import AuthenticationFailure


class ExceptionWithAttachments(Exception):
    def __init__(
        self,
        *args: Any,
        attachments: Optional[list[Path]] = None,
        **kwargs: Any,
    ):
        self.attachments = attachments


class BaseSession:
    USER_AGENT = (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) "
        "Gecko/20100101 Firefox/122.0"
    )

    @property
    def requests(self) -> requests.Session:
        if not hasattr(self, "_requests"):
            session = requests.Session()
            session.mount(
                "https://", requests.adapters.HTTPAdapter(pool_maxsize=1)
            )
            session.headers.update({"DNT": "1", "User-Agent": self.USER_AGENT})
            self._requests = session
        return self._requests


class LoginSession(BaseSession):
    def __init__(self, account: Account, debug_dir: Optional[Path]) -> None:
        self.access_token: Optional[str] = None
        self.store_id: Optional[str] = None
        self.debug_dir: Optional[Path] = debug_dir
        try:
            self._login(account)
        except ExceptionWithAttachments as e:
            raise AuthenticationFailure(
                e, account, attachments=e.attachments
            ) from e
        except Exception as e:
            raise AuthenticationFailure(e, account) from e

    @contextlib.contextmanager
    def _chrome_driver(self, headless: bool = True) -> Iterator[uc.Chrome]:
        try:
            with chrome_driver(headless=headless) as driver:
                yield driver
        except WebDriverException as e:
            attachments: list[Path] = []
            if self.debug_dir:
                path = self.debug_dir / "screenshot.png"
                with contextlib.suppress(WebDriverException):
                    driver.save_screenshot(path)
                    attachments.append(path)
            raise ExceptionWithAttachments(
                f"[{type(e).__name__}] {e}", attachments=attachments
            ) from e

    @staticmethod
    def _sign_in_success(driver: uc.Chrome) -> bool:
        try:
            element = driver.find_element(
                By.XPATH, '//span [contains(@class, "user-greeting")]'
            )
            if not (element and element.text):
                return False
            return not element.text.lower().startswith("sign in")
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def _complete_sign_in(self, driver: uc.Chrome) -> None:
        wait = WebDriverWait(driver, 30)

        def signed_in_or_verification(d: uc.Chrome) -> bool:
            return self._sign_in_success(d) or any(
                element.is_displayed()
                for element in d.find_elements(
                    By.CSS_SELECTOR, 'label #sms, label #email'
                )
            )

        wait.until(signed_in_or_verification)
        if self._sign_in_success(driver):
            return
        method = os.environ.get("SAFEWAY_VERIFICATION_METHOD", "sms")
        if method not in {"sms", "email"}:
            raise ValueError("SAFEWAY_VERIFICATION_METHOD must be sms or email")
        if not sys.stdin.isatty():
            raise RuntimeError(
                "Device verification required. Run interactively with "
                "podman run -it to enter the verification code locally."
            )
        print(f"Device verification required; selecting {method}.")
        wait.until(
            ec.element_to_be_clickable((By.ID, method))
        ).click()
        wait.until(
            ec.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Continue']")
            )
        ).click()
        print(f"Requested verification code via {method}.")

        def code_fields(d: uc.Chrome) -> Any:
            fields = d.find_elements(
                By.CSS_SELECTOR,
                'input[autocomplete="one-time-code"], '
                'input[inputmode="numeric"], input[type="tel"], '
                'input[id*="otp"], input[id*="code"], '
                'input[formcontrolname*="otp"], input[maxlength="1"]',
            )
            return [field for field in fields if field.is_displayed()]

        fields = wait.until(code_fields)
        code = input("Verification code: ").strip()
        if not code or not code.isascii() or not code.isdigit():
            raise ValueError("Verification code must contain only digits")
        if len(fields) == 1:
            fields[0].send_keys(code)
        elif len(fields) == len(code):
            for field, digit in zip(fields, code):
                field.send_keys(digit)
        else:
            raise RuntimeError("Unexpected verification code input layout")
        def submit_button(d: uc.Chrome) -> Any:
            buttons = d.find_elements(
                By.XPATH,
                "//button[normalize-space()='Verify' or "
                "normalize-space()='Continue' or "
                "normalize-space()='Verify code' or "
                "normalize-space()='Submit' or "
                "normalize-space()='Sign In' or "
                "normalize-space()='Sign in']",
            )
            return next(
                (button for button in buttons
                 if button.is_displayed() and button.is_enabled()),
                False,
            )

        print("Submit verification code")
        wait.until(submit_button).click()
        wait.until(self._sign_in_success)

    def _login(self, account: Account) -> None:
        with self._chrome_driver() as driver:
            driver.implicitly_wait(10)
            wait = WebDriverWait(driver, 10)
            # Navigate to the website URL
            url = "https://www.safeway.com"
            print("Connect to safeway.com")
            driver.get(url)
            try:
                button = driver.find_element(
                    By.XPATH,
                    "//button [contains(text(), 'Necessary Only')]",
                )
                if button:
                    print("Decline cookie prompt")
                    button.click()
                    print(
                        "Return to safeway.com after declining cookie prompt"
                    )
                    driver.get(url)
            except NoSuchElementException:
                print("Skipping cookie prompt which is not present")
            print("Open Sign In sidebar")
            wait.until(
                ec.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//span[contains(@class, 'user-greeting')]",
                    )
                )
            ).click()
            print("Open Sign In form")
            wait.until(
                ec.visibility_of_element_located(
                    (By.XPATH, "//button [contains(text(), 'Sign in')]")
                )
            ).click()
            time.sleep(2)
            print("Populate Sign In form username")
            driver.find_element(By.ID, "enterUsername").send_keys(
                account.username
            )
            time.sleep(0.5)
            print("Click Sign in with password button")
            driver.find_element(
                By.XPATH, '//button[contains(text(), "Sign in with password")]'
            ).click()
            time.sleep(2)
            driver.find_element(By.ID, "password").send_keys(account.password)
            time.sleep(0.5)
            print("Click Sign In button")
            driver.find_element(
                By.XPATH, '//button[contains(text(), "Sign In")]'
            ).click()
            time.sleep(0.5)
            print("Wait for signed in landing page to load")
            self._complete_sign_in(driver)
            print("Retrieve session information")
            session_cookie = self._parse_cookie_value(
                driver.get_cookie("SWY_SHARED_SESSION")["value"]
            )
            session_info_cookie = self._parse_cookie_value(
                driver.get_cookie("SWY_SHARED_SESSION_INFO")["value"]
            )
            self.access_token = session_cookie["accessToken"]
            try:
                self.store_id = session_info_cookie["info"]["J4U"]["storeId"]
            except Exception as e:
                raise Exception("Unable to retrieve store ID") from e

    def _parse_cookie_value(self, value: str) -> Any:
        return json.loads(urllib.parse.unquote(value))
