import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails
    currently: Password Reset + Registration Confirmation
    """

    @staticmethod
    def send_password_reset_email(user):
        """Send password reset email with link to frontend page."""
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"{settings.SITE_URL}/pages/auth/confirm_password.html?uid={uidb64}&token={token}"

        site_name = getattr(settings, 'SITE_NAME', None) or 'Fallback Site Name'

        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': site_name,
        }

        EmailService._send_templated_email(
            template_name='password_reset',
            subject='Passwort zurücksetzen',
            recipient=user.email,
            context=context
        )

    @staticmethod
    def send_registration_confirmation_email(user, token):
        """Send account activation email with link to frontend page."""
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        confirmation_url = f"{settings.SITE_URL}/pages/auth/activate.html?uid={uidb64}&token={token}"

        context = {
            'user': user,
            'confirmation_url': confirmation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Ihre Website'),
        }

        EmailService._send_templated_email(
            template_name='registration_confirmation',
            subject='Bestätige deine Registrierung',
            recipient=user.email,
            context=context
        )

    @staticmethod
    def _send_templated_email(template_name, subject, recipient, context):
        """
        Render and send a templated email.
        Always sends the text version.
        Uses HTML version if available, otherwise falls back silently to text.
        """
        try:
            # Text version is required
            message = render_to_string(f'auth_app/emails/{template_name}.txt', context=context)
        except TemplateDoesNotExist:
            logger.error(f"Required text template '{template_name}.txt' not found. Email not sent.")
            raise

        # HTML version is optional
        try:
            html_message = render_to_string(f'auth_app/emails/{template_name}.html', context=context)
        except TemplateDoesNotExist:
            html_message = None  # Silent fallback to text only

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email successfully sent to {recipient} | Subject: '{subject}'")
        except SMTPException as e:
            logger.error(f"SMTP error while sending email to {recipient}: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error while sending email to {recipient}: {e}")
            raise