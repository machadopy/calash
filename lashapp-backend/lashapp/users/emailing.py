import base64

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.signing import TimestampSigner
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


VERIFICATION_SALT = "users.email-verification"


def verification_token(user):
    return TimestampSigner(salt=VERIFICATION_SALT).sign_object(
        {"uid": user.pk, "email": user.email}
    )


def _render_email(base_name, context):
    # texto puro não deve escapar HTML (senão o & vira &amp; no link);
    # o HTML continua escapando normalmente.
    text_context = {**context, "link": mark_safe(context["link"])}
    text = render_to_string(f"users/emails/{base_name}.txt", text_context)
    html = render_to_string(f"users/emails/{base_name}.html", context)
    return text, html


def send_verification_email(user):
    token = verification_token(user)
    context = {
        "user": user,
        "link": f"{settings.FRONTEND_URL}/confirmar-email?token={token}",
        "validity": "24 horas",
    }
    text, html = _render_email("confirm_email", context)
    message = EmailMultiAlternatives(
        "Confirme seu e-mail", text, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    message.attach_alternative(html, "text/html")
    message.send()


def password_reset_link(user, token):
    uid = base64.urlsafe_b64encode(str(user.pk).encode()).decode()
    return f"{settings.FRONTEND_URL}/redefinir-senha?uid={uid}&token={token}"


def send_password_reset_email(user, token):
    context = {
        "user": user,
        "link": password_reset_link(user, token),
        "validity": "1 hora",
    }
    text, html = _render_email("reset_password", context)
    message = EmailMultiAlternatives(
        "Redefinir sua senha", text, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    message.attach_alternative(html, "text/html")
    message.send()