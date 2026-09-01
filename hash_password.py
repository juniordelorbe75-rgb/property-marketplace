from getpass import getpass

from backend.auth.security import hash_password

password = getpass("Password to hash: ")

if not password:
    raise SystemExit("Password cannot be empty")

hashed_password = hash_password(password)

print(hashed_password)
