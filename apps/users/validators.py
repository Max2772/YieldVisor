"""Validators to reduce automated signup spam."""

import re

from django.core.exceptions import ValidationError

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
DISPOSABLE_EMAIL_DOMAINS = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "10minutemail.com",
        "tempmail.com",
        "yopmail.com",
    }
)


def validate_registration_username(value: str) -> None:
    if not USERNAME_RE.match(value):
        raise ValidationError("Имя пользователя: 3–32 символа, только латиница, цифры и подчёркивание.")


def validate_registration_email(value: str) -> None:
    domain = value.rsplit("@", 1)[-1].lower()
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        raise ValidationError("Временные почтовые ящики не поддерживаются.")


def validate_registration_display_name(value: str, *, field_label: str) -> None:
    cleaned = value.strip()
    if len(cleaned) > 50:
        raise ValidationError(f"{field_label}: не более 50 символов.")
    if len(cleaned) >= 3 and cleaned.isdigit():
        raise ValidationError(f"{field_label}: некорректное значение.")
