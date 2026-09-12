from unittest.mock import MagicMock, patch

import pytest

from safeway_coupons.session import LoginSession


@pytest.mark.parametrize("method", ["sms", "email"])
def test_verification(method, monkeypatch):
    monkeypatch.setenv("SAFEWAY_VERIFICATION_METHOD", method)
    session = LoginSession.__new__(LoginSession)
    driver = MagicMock()
    field = MagicMock()
    submit = MagicMock()

    def find_buttons(by, selector):
        assert "normalize-space()='Sign In'" in selector
        return [submit]

    driver.find_elements.side_effect = find_buttons

    def submit_condition(condition):
        return condition(driver)
    with (
        patch.object(session, "_sign_in_success", return_value=False),
        patch("safeway_coupons.session.sys.stdin.isatty", return_value=True),
        patch("builtins.input", return_value="123456") as code_input,
        patch("safeway_coupons.session.WebDriverWait") as wait,
    ):
        results = iter([True, MagicMock(), MagicMock(), [field]])

        def until(condition):
            result = next(results, None)
            if result is not None:
                return result
            if getattr(condition, "__name__", "") == "submit_button":
                return submit_condition(condition)
            return True

        wait.return_value.until.side_effect = until
        session._complete_sign_in(driver)
    code_input.assert_called_once_with("Verification code: ")
    field.send_keys.assert_called_once_with("123456")
    submit.click.assert_called_once_with()


def test_verification_requires_terminal():
    session = LoginSession.__new__(LoginSession)
    driver = MagicMock()
    with (
        patch.object(session, "_sign_in_success", return_value=False),
        patch("safeway_coupons.session.sys.stdin.isatty", return_value=False),
    ):
        with pytest.raises(RuntimeError, match="Device verification required"):
            session._complete_sign_in(driver)
    driver.find_element.assert_not_called()


def test_verification_detects_visible_label_with_hidden_radio():
    session = LoginSession.__new__(LoginSession)
    driver = MagicMock()
    hidden_radio = MagicMock()
    hidden_radio.is_displayed.return_value = False
    label = MagicMock()
    label.is_displayed.return_value = True
    driver.find_elements.side_effect = lambda by, selector: (
        [label] if selector == 'label #sms, label #email' else [hidden_radio]
    )

    def check_condition(condition):
        assert condition(driver) is True

    with (
        patch.object(session, "_sign_in_success", return_value=False),
        patch("safeway_coupons.session.sys.stdin.isatty", return_value=False),
        patch("safeway_coupons.session.WebDriverWait") as wait,
    ):
        wait.return_value.until.side_effect = check_condition
        with pytest.raises(RuntimeError, match="Device verification required"):
            session._complete_sign_in(driver)
