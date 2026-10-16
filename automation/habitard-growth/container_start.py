"""Prepare the mounted data directory, then drop privileges before serving."""
import os
from pathlib import Path
import pwd
import sys


def main():
    if os.geteuid() == 0:
        account = pwd.getpwnam('habitard')
        database = Path(os.environ.get('DATABASE_PATH', '/data/habitard.db'))
        database.parent.mkdir(parents=True, exist_ok=True)
        os.chown(database.parent, account.pw_uid, account.pw_gid)
        os.chmod(database.parent, 0o700)
        for path in (database, Path(str(database) + '-wal'), Path(str(database) + '-shm')):
            if path.exists():
                os.chown(path, account.pw_uid, account.pw_gid)
        os.setgroups([])
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
    os.execv(sys.executable, [sys.executable, 'app.py'])


if __name__ == '__main__':
    main()
