import os
import smtplib
import ssl
from email.message import EmailMessage

from backend.config import parse_boolean_setting, parse_bounded_integer_setting


def deliver_email(message: EmailMessage) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        return False

    port = parse_bounded_integer_setting(
        "SMTP_PORT", os.getenv("SMTP_PORT"), default=587, minimum=1, maximum=65535
    )
    timeout = parse_bounded_integer_setting(
        "SMTP_TIMEOUT_SECONDS", os.getenv("SMTP_TIMEOUT_SECONDS"),
        default=10, minimum=1, maximum=60,
    )
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = parse_boolean_setting("SMTP_USE_TLS", os.getenv("SMTP_USE_TLS"), default=True)

    with smtplib.SMTP(host, port, timeout=timeout) as smtp:
        smtp.ehlo()
        if use_tls:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
    return True
