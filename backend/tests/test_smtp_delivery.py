import os
import unittest
from email.message import EmailMessage
from unittest.mock import Mock, patch

from backend.services.smtp_delivery import deliver_email


class SmtpDeliveryTests(unittest.TestCase):
    def test_missing_host_keeps_local_delivery_disabled(self):
        with patch.dict(os.environ, {"SMTP_HOST": ""}, clear=False):
            self.assertFalse(deliver_email(EmailMessage()))

    def test_delivery_uses_bounded_timeout_tls_and_authentication(self):
        message = EmailMessage()
        message["From"] = "HabitaRD <no-reply@habitard.com.do>"
        message["To"] = "member@example.com"
        message["Subject"] = "HabitaRD"
        message.set_content("Mensaje")
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=False)
        settings = {
            "SMTP_HOST": "smtp.provider.test",
            "SMTP_PORT": "2525",
            "SMTP_TIMEOUT_SECONDS": "12",
            "SMTP_USE_TLS": "true",
            "SMTP_USERNAME": "mailer",
            "SMTP_PASSWORD": "secret",
        }

        with patch.dict(os.environ, settings, clear=False), patch(
            "backend.services.smtp_delivery.smtplib.SMTP", return_value=smtp
        ) as smtp_factory:
            self.assertTrue(deliver_email(message))

        smtp_factory.assert_called_once_with("smtp.provider.test", 2525, timeout=12)
        self.assertEqual(smtp.ehlo.call_count, 2)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("mailer", "secret")
        smtp.send_message.assert_called_once_with(message)
