"""Launch the local review dashboard from PyCharm without cloud credentials."""
import os
from pathlib import Path
import runpy
import secrets


def main():
    folder = Path(__file__).resolve().parent
    os.environ['HOST'] = '127.0.0.1'
    os.environ['PORT'] = '8010'
    os.environ['DATABASE_PATH'] = str(folder / 'data' / 'habitard-local.db')
    for channel in ('EMAIL_ENABLED', 'INSTAGRAM_ENABLED', 'DISCOVERY_ENABLED'):
        os.environ[channel] = 'false'
    # Credentials remain in memory and the local Run console, never in Git.
    password = secrets.token_urlsafe(24)
    os.environ['ADMIN_PASSWORD'] = password
    print('Habitard local dashboard: http://127.0.0.1:8010', flush=True)
    print('Username: admin', flush=True)
    print('Temporary password: ' + password, flush=True)
    print('Email, Instagram publishing and scheduled discovery are OFF.', flush=True)
    print('Stop the Run session to shut down the dashboard.', flush=True)
    runpy.run_path(str(folder / 'app.py'), run_name='__main__')


if __name__ == '__main__':
    main()
