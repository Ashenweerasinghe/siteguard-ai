"""Generate a password hash for .streamlit/secrets.toml or SITEGUARD_USERS.

    python scripts/hash_password.py

Then add to .streamlit/secrets.toml:

    [users.jdoe]
    name = "Jane Doe"
    role = "Safety Officer"
    password_hash = "pbkdf2$200000$..."
"""

import getpass
import hashlib
import secrets


def main() -> None:
    pw = getpass.getpass("New password: ")
    if pw != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000)
    print(f"pbkdf2$200000${salt}${digest.hex()}")


if __name__ == "__main__":
    main()
