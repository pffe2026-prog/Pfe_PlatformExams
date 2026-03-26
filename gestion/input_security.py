import re

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

MAX_SEARCH_TERM_LENGTH = 80
MAX_SOURCE_CODE_LENGTH = 50000

_DANGEROUS_HTML_PATTERNS = (
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"<\s*(iframe|object|embed|svg|img|style|link|meta)", re.IGNORECASE),
)
_SEARCH_INVALID_CHARS_RE = re.compile(r"[^\w\s@.\-']", re.UNICODE)


def clean_plain_text(value, field_label):
    text = (value or "").replace("\x00", "").strip()
    if not text:
        return text

    if strip_tags(text) != text or any(pattern.search(text) for pattern in _DANGEROUS_HTML_PATTERNS):
        raise ValidationError(
            f"{field_label} ne doit pas contenir de balises HTML ou de code JavaScript."
        )
    return text


def clean_search_term(value, max_length=MAX_SEARCH_TERM_LENGTH):
    text = (value or "").replace("\x00", "").strip()
    if not text:
        return ""

    if strip_tags(text) != text or any(pattern.search(text) for pattern in _DANGEROUS_HTML_PATTERNS):
        return ""

    text = _SEARCH_INVALID_CHARS_RE.sub(" ", text[:max_length])
    return " ".join(text.split())


def clean_digit_filter(value, max_length=20):
    text = (value or "").replace("\x00", "").strip()
    if not text:
        return ""

    text = text[:max_length]
    return text if text.isdigit() else ""


def validate_source_code(value):
    text = (value or "").replace("\x00", "")
    if len(text) > MAX_SOURCE_CODE_LENGTH:
        raise ValidationError(
            f"Le code source est trop long (maximum {MAX_SOURCE_CODE_LENGTH} caracteres)."
        )
    return text
