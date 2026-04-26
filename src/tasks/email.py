import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from celery_app import app
from core.config import settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


def send_email(to: str, subject: str, template_name: str, **context: str) -> None:
    """Send an email using the given template."""
    html = templates.get_template(f"{template_name}.html").render(**context)
    plain = templates.get_template(f"{template_name}.txt").render(**context)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.send_message(msg)


@app.task(
    autoretry_for=(smtplib.SMTPException, ConnectionError, OSError),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
    acks_late=True,
)
def send_activation_email(email: str, token: str) -> None:
    url = f"{settings.frontend_url}/activate?token={token}"
    send_email(email, "Activate your account", "activation_email", url=url)


@app.task(
    autoretry_for=(smtplib.SMTPException, ConnectionError, OSError),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=5,
    acks_late=True,
)
def send_password_reset_email(email: str, token: str) -> None:
    url = f"{settings.frontend_url}/reset-password?token={token}"
    send_email(email, "Reset your password", "password_reset_email", url=url)
