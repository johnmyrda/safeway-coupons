#!/usr/bin/env python3
"""Prompt locally for credentials; never pass them as command arguments."""
import configparser
import getpass
import os
from pathlib import Path

root = Path(__file__).resolve().parent.parent
path = root / "accounts"
if path.exists():
    raise SystemExit("accounts already exists; edit it locally or remove it first.")
username = input("Safeway account email: ").strip()
password = getpass.getpass("Safeway account password: ")
if not username or not password or any(c in username for c in "[]\r\n"):
    raise SystemExit("A valid email and nonempty password are required.")
config = configparser.ConfigParser()
# The application's ConfigParser interpolates %, so escape literal percent signs.
config[username] = {"password": password.replace("%", "%%")}
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as stream:
    config.write(stream)
print("Saved credentials to git-ignored accounts (permissions 0600).")
