"""Habitard's single-instance cloud worker and private review dashboard."""
import base64
import hmac
import html
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import threading
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse, urljoin
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).parent
DB = os.getenv('DATABASE_PATH', str(ROOT / 'data' / 'habitard.db'))
LOCK = threading.RLock()
UA = 'HabitardContactResearch/1.0'


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=30, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS contacts (
          id INTEGER PRIMARY KEY, business TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
          market TEXT NOT NULL DEFAULT '', source TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'research', eligibility TEXT NOT NULL DEFAULT '',
          discovered TEXT NOT NULL, sent_at TEXT, result TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS posts (
          id INTEGER PRIMARY KEY, caption TEXT NOT NULL, image_url TEXT NOT NULL,
          scheduled TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
          container TEXT, result TEXT NOT NULL DEFAULT '', published_at TEXT);
        CREATE TABLE IF NOT EXISTS suppression (email TEXT PRIMARY KEY, reason TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, at TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
        ''')
        # Never automatically retry an external operation interrupted by a restart.
        db.execute("UPDATE contacts SET status='uncertain' WHERE status='sending'")
        db.execute("UPDATE posts SET status='uncertain' WHERE status='publishing'")
    seed = ROOT / 'seed.json'
    if seed.exists():
        for row in json.loads(seed.read_text(encoding='utf-8'))['prospects']:
            add_contact(row)


def now():
    return datetime.now(timezone.utc).isoformat()


def event(kind, detail):
    with connect() as db:
        db.execute('INSERT INTO events(at,kind,detail) VALUES (?,?,?)', (now(), kind, detail))


def add_contact(row):
    email = row['email'].strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise ValueError('Invalid email')
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO contacts(business,email,market,source,discovered) VALUES (?,?,?,?,?)',
                   (row['business'], email, row.get('market', ''), row['source'], now()))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_url(url):
    p = urlparse(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Use a public HTTPS URL without credentials or a custom port')
    addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
        raise ValueError('Private and local network destinations are blocked')
    return url


def fetch(url, data=None, headers=None, public=False):
    if public:
        public_url(url)
    request = Request(url, data=data, headers={'User-Agent': UA, **(headers or {})})
    # No redirects: a public page cannot redirect the crawler into a private network.
    with build_opener(NoRedirect).open(request, timeout=25) as response:
        content = response.read(2_000_001)
        if len(content) > 2_000_000:
            raise ValueError('Response exceeds 2 MB limit')
        return content


def api(url, fields=None, token=None):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
    data = urlencode(fields).encode() if fields is not None else None
    return json.loads(fetch(url, data, headers))


def discover(row):
    """Inspect one owner-selected business page. Does not crawl an entire site."""
    url = public_url(row['source'])
    robot_url = urljoin(url, '/robots.txt')
    robots = RobotFileParser()
    try:
        robots.parse(fetch(robot_url, public=True).decode('utf-8', errors='replace').splitlines())
    except HTTPError as exc:
        if exc.code != 404:
            raise ValueError('Cannot establish crawl permission') from None
        robots.parse([])
    if not robots.can_fetch(UA, url):
        raise ValueError('The website disallows this crawler')
    page = html.unescape(fetch(url, public=True).decode('utf-8', errors='replace'))
    emails = set(re.findall(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}', page))
    for email in sorted(emails):
        if not email.lower().endswith(('.png', '.jpg', '.webp', '.svg')):
            add_contact({**row, 'email': email})
    event('discovery', f'Inspected one page; found {len(emails)} candidate addresses')


def discover_search():
    key = os.getenv('BRAVE_SEARCH_API_KEY')
    if not key:
        return
    query = os.getenv('DISCOVERY_QUERY', 'inmobiliaria Republica Dominicana contacto email')
    results = json.loads(fetch('https://api.search.brave.com/res/v1/web/search?' + urlencode({'q': query, 'count': 10}),
                               headers={'X-Subscription-Token': key}))
    for result in results.get('web', {}).get('results', []):
        try:
            discover({'business': result['title'], 'source': result['url'], 'market': 'Dominican Republic (review required)'})
        except Exception as exc:
            event('discovery_error', type(exc).__name__)
        time.sleep(2)


def invitation(contact):
    sender = os.getenv('SENDER_NAME', '')
    address = os.getenv('BUSINESS_ADDRESS', '')
    return (f"Hola, equipo de {contact['business']}:\n\n"
            f"Soy {sender}, de Habitard, un marketplace de propiedades. Encontré su agencia en {contact['source']} "
            "y me gustaría invitarles a registrarse y publicar sus propiedades en venta o alquiler.\n\n"
            "Conozcan la plataforma y creen su cuenta aquí:\nhttps://habitard-marketplace.netlify.app/\n\n"
            "¿Les interesaría probarla con una de sus propiedades?\n\n"
            f"Saludos,\n{sender}\nHabitard\n{address}\n\n"
            "Si prefieren no recibir más mensajes, respondan «No contactar».\n")


def gmail_send(contact):
    required = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REFRESH_TOKEN', 'SENDER_EMAIL', 'SENDER_NAME', 'BUSINESS_ADDRESS']
    if any(not os.getenv(k) for k in required):
        raise ValueError('Gmail connection or sender details missing')
    token = api('https://oauth2.googleapis.com/token', {
        'client_id': os.environ['GOOGLE_CLIENT_ID'], 'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
        'refresh_token': os.environ['GOOGLE_REFRESH_TOKEN'], 'grant_type': 'refresh_token'})['access_token']
    message = EmailMessage()
    message['From'] = f"{os.environ['SENDER_NAME']} <{os.environ['SENDER_EMAIL']}>"
    message['To'] = contact['email']
    message['Subject'] = 'Invitación a publicar tus propiedades en Habitard'
    message.set_content(invitation(contact))
    data = json.dumps({'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}).encode()
    return json.loads(fetch('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', data,
                           {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}))['id']


def instagram_publish(post):
    account = os.environ['INSTAGRAM_ACCOUNT_ID']
    version = os.environ['META_API_VERSION']
    if not re.fullmatch(r'v\d+\.\d+', version) or not account.isdigit():
        raise ValueError('Invalid Meta version or account ID')
    token = os.environ['INSTAGRAM_ACCESS_TOKEN']
    base = f'https://graph.instagram.com/{version}'
    container = post['container']
    if not container:
        container = api(f'{base}/{account}/media', {'image_url': post['image_url'], 'caption': post['caption']}, token)['id']
        with connect() as db:
            db.execute('UPDATE posts SET container=? WHERE id=?', (container, post['id']))
    for _ in range(12):
        status = api(f'{base}/{container}?fields=status_code', token=token)['status_code']
        if status == 'FINISHED':
            break
        if status in ('ERROR', 'EXPIRED', 'PUBLISHED'):
            raise ValueError('Container requires review: ' + status)
        time.sleep(5)
    else:
        raise TimeoutError('Container not ready; review before retry')
    return api(f'{base}/{account}/media_publish', {'creation_id': container}, token)['id']


def tick():
    with LOCK, connect() as db:
        if os.getenv('EMAIL_ENABLED') == 'true':
            limit = int(os.getenv('EMAIL_DAILY_LIMIT', '10'))
            count = db.execute("SELECT count(*) FROM contacts WHERE sent_at>=?", (now()[:10],)).fetchone()[0]
            contact = db.execute("SELECT * FROM contacts WHERE status='approved' AND eligibility!='' AND email NOT IN (SELECT email FROM suppression) ORDER BY id LIMIT 1").fetchone()
            # One invitation per tick; in-flight/uncertain sends consume a daily slot too.
            if contact and count < limit:
                db.execute("UPDATE contacts SET status='sending',sent_at=? WHERE id=?", (now(), contact['id']))
                db.commit()
                try:
                    result = gmail_send(contact)
                    db.execute("UPDATE contacts SET status='sent',result=? WHERE id=?", (result, contact['id']))
                except Exception as exc:
                    db.execute("UPDATE contacts SET status='uncertain',result=? WHERE id=?", (type(exc).__name__ + ': review provider before any retry', contact['id']))
                db.commit()
        if os.getenv('INSTAGRAM_ENABLED') == 'true':
            already = db.execute('SELECT 1 FROM posts WHERE published_at>=? LIMIT 1', (now()[:10],)).fetchone()
            unresolved = db.execute("SELECT 1 FROM posts WHERE status='uncertain' LIMIT 1").fetchone()
            post = db.execute("SELECT * FROM posts WHERE status='approved' AND scheduled<=? ORDER BY scheduled,id LIMIT 1", (now(),)).fetchone()
            if post and not already and not unresolved:
                db.execute("UPDATE posts SET status='publishing' WHERE id=?", (post['id'],))
                db.commit()
                try:
                    result = instagram_publish(post)
                    db.execute("UPDATE posts SET status='published',result=?,published_at=? WHERE id=?", (result, now(), post['id']))
                except Exception as exc:
                    db.execute("UPDATE posts SET status='uncertain',result=? WHERE id=?", (type(exc).__name__ + ': review Instagram before any retry', post['id']))


def action(payload):
    with LOCK, connect() as db:
        op = payload['action']
        if op == 'discover':
            discover(payload)
        elif op == 'approve_contact':
            reason = payload.get('eligibility', '').strip()
            if not reason:
                raise ValueError('Record why this recipient is eligible for outreach')
            db.execute("UPDATE contacts SET status='approved',eligibility=? WHERE id=? AND status='research' AND email NOT IN (SELECT email FROM suppression)", (reason, int(payload['id'])))
        elif op == 'suppress':
            email = payload['email'].strip().lower()
            db.execute('INSERT OR REPLACE INTO suppression VALUES (?,?)', (email, payload.get('reason', 'opt-out')))
            db.execute("UPDATE contacts SET status='suppressed' WHERE email=?", (email,))
        elif op == 'add_post':
            public_url(payload['image_url'])
            scheduled = datetime.fromisoformat(payload['scheduled'].replace('Z', '+00:00'))
            if scheduled.tzinfo is None:
                raise ValueError('Scheduled time must include timezone')
            caption = payload['caption'].strip()
            if not caption or len(caption) > 2200:
                raise ValueError('Caption must be 1–2200 characters')
            db.execute('INSERT INTO posts(caption,image_url,scheduled) VALUES (?,?,?)',
                       (caption, payload['image_url'], scheduled.astimezone(timezone.utc).isoformat()))
        elif op == 'approve_post':
            db.execute("UPDATE posts SET status='approved' WHERE id=? AND status='draft'", (int(payload['id']),))
        else:
            raise ValueError('Unknown action')


def snapshot():
    with connect() as db:
        return {
            'contacts': [{**dict(r), 'preview': invitation(r)} for r in db.execute('SELECT * FROM contacts ORDER BY id')],
            'posts': [dict(r) for r in db.execute('SELECT * FROM posts ORDER BY scheduled')],
            'events': [dict(r) for r in db.execute('SELECT * FROM events ORDER BY id DESC LIMIT 30')],
            'email_enabled': os.getenv('EMAIL_ENABLED') == 'true',
            'instagram_enabled': os.getenv('INSTAGRAM_ENABLED') == 'true',
            'notice': 'No follow-ups. Record replies, opt-outs and bounces with Suppress before further outreach. Dates are UTC.'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Avoid logging credentials, query strings, or prospect information.

    def reply(self, status, body, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def authorized(self):
        expected = 'Basic ' + base64.b64encode(('admin:' + os.environ['ADMIN_PASSWORD']).encode()).decode()
        if hmac.compare_digest(self.headers.get('Authorization', ''), expected):
            return True
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Habitard"')
        self.end_headers()
        return False

    def do_GET(self):
        if self.path == '/health':
            return self.reply(200, {'ok': True})
        if not self.authorized():
            return
        if self.path == '/':
            return self.reply(200, (ROOT / 'dashboard.html').read_bytes(), 'text/html; charset=utf-8')
        if self.path == '/api/state':
            return self.reply(200, snapshot())
        self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.authorized():
            return
        # Custom header blocks cross-origin HTML form submissions; no CORS enabled.
        if self.path != '/api/action' or self.headers.get('X-Habitard-Action') != 'review':
            return self.reply(403, {'error': 'Invalid request'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000:
                raise ValueError('Request too large or empty')
            action(json.loads(self.rfile.read(length)))
            self.reply(200, {'ok': True})
        except (ValueError, KeyError) as exc:
            self.reply(400, {'error': str(exc)})
        except Exception as exc:
            event('request_error', type(exc).__name__)
            self.reply(502, {'error': 'External request failed; see activity log'})


def worker():
    next_discovery = time.monotonic() + 60
    while True:
        try:
            tick()
            if os.getenv('DISCOVERY_ENABLED') == 'true' and time.monotonic() >= next_discovery:
                next_discovery = time.monotonic() + 86400
                discover_search()
        except Exception as exc:
            event('worker_error', type(exc).__name__)
        time.sleep(60)


if __name__ == '__main__':
    if len(os.getenv('ADMIN_PASSWORD', '')) < 20:
        raise SystemExit('Set ADMIN_PASSWORD to a unique password of at least 20 characters')
    initialize()
    threading.Thread(target=worker, daemon=True).start()
    ThreadingHTTPServer((os.getenv('HOST', '127.0.0.1'), int(os.getenv('PORT', '8000'))), Handler).serve_forever()
