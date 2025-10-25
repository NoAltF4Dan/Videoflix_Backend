import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.template.exceptions import TemplateDoesNotExist
from django.contrib.auth.tokens import default_token_generator
from smtplib import SMTPException

logger = logging.getLogger(__name__)


class EmailService:
    """
    Utility for dispatching emails, handling password resets and registration confirmations.
    """

    @staticmethod
    def send_password_reset_email(user):
        """
        Sends an email with a password reset link to the user.
        """
        reset_token = default_token_generator.make_token(user)
        encoded_uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{settings.SITE_URL}/pages/auth/confirm_password.html?uid={encoded_uid}&token={reset_token}"

        site_title = getattr(settings, 'SITE_NAME', 'Default Site Name')

        email_context = {
            'user': user,
            'reset_link': reset_link,
            'site_title': site_title,
        }

        EmailService._send_templated_email(
            subject='Passwort zurücksetzen',
            template_name='password_reset',
            recipient=user.email,
            context=email_context
        )

    @staticmethod
    def send_registration_confirmation_email(user, token):
        """
        Sends an email with an account activation link to the user.
        """
        encoded_uid = urlsafe_base64_encode(force_bytes(user.pk))
        activation_link = f"{settings.SITE_URL}/pages/auth/activate.html?uid={encoded_uid}&token={token}"

        email_context = {
            'user': user,
            'activation_link': activation_link,
            'site_title': getattr(settings, 'SITE_NAME', 'Ihre Website'),
        }

        EmailService._send_templated_email(
            subject='Bestätige deine Registrierung',
            template_name='registration_confirmation',
            recipient=user.email,
            context=email_context
        )

    @staticmethod
    def _send_templated_email(subject, template_name, recipient, context):
        """
        Sends an email using a rendered template. Requires a text version; HTML is optional.
        Falls back to text if HTML template is missing.
        """
        try:
            text_content = render_to_string(f'auth_app/emails/{template_name}.txt', context=context)
        except TemplateDoesNotExist:
            logger.error(f"Text template '{template_name}.txt' missing. Email dispatch aborted.")
            raise

        html_content = None
        try:
            html_content = render_to_string(f'auth_app/emails/{template_name}.html', context=context)
        except TemplateDoesNotExist:
            pass  # HTML is optional, silently fall back to text

        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info(f"Successfully sent email to {recipient} | Subject: '{subject}'")
        except SMTPException as err:
            logger.error(f"SMTP failure during email dispatch to {recipient}: {err}")
            raise
        except Exception as err:
            logger.exception(f"Unexpected issue during email dispatch to {recipient}: {err}")
            raise