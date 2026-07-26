from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.http import urlencode


def send_activation_email(
    *,
    request: HttpRequest,
    email: str,
    activation_token: str,
) -> None:
    activation_url = build_absolute_url(
        request,
        reverse("web:activate"),
        {"token": activation_token},
    )
    send_account_email(
        subject="Activate your City Guide account",
        template_name="emails/verify_email.html",
        to_email=email,
        context={
            "activation_url": activation_url,
        },
    )


def send_password_reset_email(
    *,
    request: HttpRequest,
    email: str,
    reset_token: str,
) -> None:
    reset_url = build_absolute_url(
        request,
        reverse("web:reset_password"),
        {"token": reset_token},
    )
    send_account_email(
        subject="Reset your City Guide password",
        template_name="emails/password_reset.html",
        to_email=email,
        context={
            "reset_url": reset_url,
            "reset_token": reset_token,
        },
    )


def send_account_email(
    *,
    subject: str,
    template_name: str,
    to_email: str,
    context: dict[str, str],
) -> None:
    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html_body, "text/html")
    message.send()


def build_absolute_url(
    request: HttpRequest,
    path: str,
    query_params: dict[str, str],
) -> str:
    return request.build_absolute_uri(f"{path}?{urlencode(query_params)}")
