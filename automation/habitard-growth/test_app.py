import os
import tempfile
import unittest
import base64
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import app
import run_local
from xml.etree import ElementTree


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = app.DB
        app.DB = self.tmp.name + '/test.db'
        self.env = patch.dict(os.environ, {'EMAIL_ENABLED': 'true', 'EMAIL_DAILY_LIMIT': '1', 'INSTAGRAM_ENABLED': 'false'}, clear=False)
        self.env.start()
        app.initialize()
        # Remove seed contacts so all tests use invented addresses only.
        with app.connect() as db:
            db.execute('DELETE FROM contacts')
        app.add_contact({'business': 'Example Agency', 'email': 'agent@example.com', 'source': 'https://example.com/contact'})

    def tearDown(self):
        self.env.stop()
        app.DB = self.old_db
        self.tmp.cleanup()

    def approve(self):
        contact = app.snapshot()['contacts'][0]
        app.action({'action': 'approve_contact', 'id': contact['id'], 'eligibility': 'Test permission'})

    @patch('app.gmail_send', return_value='message-1')
    def test_research_never_sends_and_approved_sends_once(self, send):
        app.tick()
        send.assert_not_called()
        self.approve()
        app.tick()
        app.tick()
        self.assertEqual(send.call_count, 1)
        self.assertEqual(app.snapshot()['contacts'][0]['status'], 'sent')

    @patch('app.gmail_send')
    def test_suppression_blocks_approved_recipient(self, send):
        self.approve()
        app.action({'action': 'suppress', 'email': 'AGENT@example.com'})
        app.tick()
        send.assert_not_called()

    @patch('app.gmail_send', side_effect=TimeoutError())
    def test_uncertain_send_is_not_retried_after_restart(self, send):
        self.approve()
        app.tick()
        app.initialize()
        app.tick()
        self.assertEqual(send.call_count, 1)
        self.assertEqual(app.snapshot()['contacts'][0]['status'], 'uncertain')

    @patch('app.gmail_send', return_value='message-1')
    def test_daily_limit(self, send):
        self.approve()
        app.add_contact({'business': 'Second Agency', 'email': 'second@example.com', 'source': 'https://example.org'})
        second = app.snapshot()['contacts'][1]
        app.action({'action': 'approve_contact', 'id': second['id'], 'eligibility': 'Test permission'})
        app.tick()
        app.tick()
        self.assertEqual(send.call_count, 1)

    def test_email_deduplication(self):
        app.add_contact({'business': 'Duplicate', 'email': 'AGENT@example.com', 'source': 'https://example.com'})
        self.assertEqual(len(app.snapshot()['contacts']), 1)

    def test_approval_requires_recorded_basis(self):
        with self.assertRaises(ValueError):
            app.action({'action': 'approve_contact', 'id': 1, 'eligibility': ''})

    def test_dashboard_authentication_and_mutation_protection(self):
        with patch.dict(os.environ, {'ADMIN_PASSWORD': 'test-only-password-not-a-real-secret'}):
            server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_address[1]}'
            auth = 'Basic ' + base64.b64encode(b'admin:test-only-password-not-a-real-secret').decode()
            try:
                with self.assertRaises(HTTPError) as denied:
                    urlopen(base + '/api/state')
                self.assertEqual(denied.exception.code, 401)
                denied.exception.close()
                with urlopen(Request(base + '/', headers={'Authorization': auth})) as response:
                    self.assertIn(b'Growth desk', response.read())
                with urlopen(Request(base + '/api/state', headers={'Authorization': auth})) as response:
                    self.assertEqual(len(json.load(response)['contacts']), 1)
                request = Request(base + '/api/action', data=b'{"action":"suppress","email":"agent@example.com"}', headers={'Authorization': auth})
                with self.assertRaises(HTTPError) as denied:
                    urlopen(request)
                self.assertEqual(denied.exception.code, 403)
                denied.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_blocks_private_network(self):
        with self.assertRaises(ValueError):
            app.public_url('https://127.0.0.1/')
        with self.assertRaises(ValueError):
            app.public_url('http://example.com/')

    def test_pycharm_launcher_pauses_channels_and_uses_local_database(self):
        with patch.dict(os.environ, {'EMAIL_ENABLED': 'true', 'INSTAGRAM_ENABLED': 'true', 'DISCOVERY_ENABLED': 'true'}):
            with patch('run_local.runpy.run_path') as run, patch('builtins.print'):
                run_local.main()
                self.assertEqual(os.environ['HOST'], '127.0.0.1')
                self.assertEqual(os.environ['PORT'], '8010')
                self.assertTrue(os.environ['DATABASE_PATH'].endswith('habitard-local.db'))
                for channel in ('EMAIL_ENABLED', 'INSTAGRAM_ENABLED', 'DISCOVERY_ENABLED'):
                    self.assertEqual(os.environ[channel], 'false')
                self.assertGreaterEqual(len(os.environ['ADMIN_PASSWORD']), 20)
                run.assert_called_once()

    def test_pycharm_configuration_points_to_launcher(self):
        project = app.ROOT.parents[1]
        configuration = project / '.run' / 'Habitard Growth Local.run.xml'
        if not configuration.exists():
            self.skipTest('Run configuration is checked at repository root')
        root = ElementTree.parse(configuration).getroot()
        script = root.find(".//option[@name='SCRIPT_NAME']")
        self.assertEqual(script.attrib['value'], '$PROJECT_DIR$/automation/habitard-growth/run_local.py')

    @patch('app.public_url', side_effect=lambda url: url)
    @patch('app.instagram_publish', return_value='media-1')
    def test_posts_require_approval_and_only_one_per_utc_day(self, publish, _):
        with patch.dict(os.environ, {'INSTAGRAM_ENABLED': 'true', 'EMAIL_ENABLED': 'false'}):
            for caption in ('First', 'Second'):
                app.action({'action': 'add_post', 'caption': caption, 'image_url': 'https://example.com/photo.jpg', 'scheduled': '2020-01-01T12:00:00Z'})
            app.tick()
            publish.assert_not_called()
            for post in app.snapshot()['posts']:
                app.action({'action': 'approve_post', 'id': post['id']})
            app.tick()
            app.tick()
            self.assertEqual(publish.call_count, 1)

    @patch('app.public_url', side_effect=lambda url: url)
    @patch('app.instagram_publish', side_effect=TimeoutError())
    def test_uncertain_post_pauses_further_publication(self, publish, _):
        with patch.dict(os.environ, {'INSTAGRAM_ENABLED': 'true', 'EMAIL_ENABLED': 'false'}):
            app.action({'action': 'add_post', 'caption': 'Test', 'image_url': 'https://example.com/photo.jpg', 'scheduled': '2020-01-01T12:00:00Z'})
            app.action({'action': 'approve_post', 'id': app.snapshot()['posts'][0]['id']})
            app.tick()
            app.tick()
            self.assertEqual(publish.call_count, 1)


if __name__ == '__main__':
    unittest.main()
