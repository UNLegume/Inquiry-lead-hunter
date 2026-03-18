"""Noise filter: removes auto-replies, newsletters, and bounce messages."""

import logging
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from inquiry_lead_hunter.models import Email

logger = logging.getLogger(__name__)


def _extract_sender_domain(sender: str) -> str:
    """Extract the domain part from an email sender string.

    Handles both plain ``user@domain.com`` and display-name format
    ``"Name <user@domain.com>"``.  Returns an empty string if no domain
    can be found.
    """
    match = re.search(r"<[^>]*@([^>]+)>", sender)
    if not match:
        match = re.search(r"@([\w.\-]+)", sender)
    if match:
        return match.group(1).lower()
    return ""


def _strip_quoted_reply(body: str) -> str:
    """Remove quoted reply sections from email body, returning only the new content.

    Detects common quote markers (Japanese/English Gmail, Outlook, forwarded)
    and returns only the text before the first marker.  If the marker appears
    at the very beginning (i.e. the stripped result is empty), the original
    body is returned as-is to avoid losing all content.
    """
    markers = [
        # Japanese Gmail: 2024年3月15日(金) 10:30
        r"\d{4}年\d{1,2}月\d{1,2}日\s*[\(（].[\)）]\s*\d{1,2}:\d{1,2}",
        # English Gmail: On Mon, Mar 15, 2024 at 10:30 AM ... wrote:
        r"^On\s+.+\s+wrote:\s*$",
        # English Gmail attribution without "wrote:" (Japanese email clients)
        r"^On\s+\w{3},\s+\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}",
        # Outlook / forwarded
        r"---+\s*(?:Original Message|元のメッセージ|Forwarded message|転送メッセージ)",
        # Outlook English: From: header
        r"^From:\s+.+\s*<[^>]+@[^>]+>",
        # Outlook Japanese: 差出人 header
        r"^差出人[:：]",
        # Outlook underscore separator
        r"_{20,}",
        # Em dash separator (─ U+2500, ━ U+2501)
        r"[─━]{4,}",
        # > prefix with date header (e.g., > 2026/02/19 22:00、xxx@example.comのメール:)
        r"^>\s*\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{1,2}",
    ]
    pattern = "|".join(f"(?:{m})" for m in markers)
    match = re.search(pattern, body, re.MULTILINE)
    marker_stripped = False
    if match:
        before = body[: match.start()].rstrip()
        if before:
            body = before
            marker_stripped = True

    # Also remove > prefixed quoted lines (standard email quoting).
    # Apply when either a marker was found and stripped, or when no marker was
    # found at all (so lone > lines still get removed).  Skip when the marker
    # was at the very beginning and we fell back to the full original body.
    if marker_stripped or not match:
        lines = body.split("\n")
        cleaned = [line for line in lines if not re.match(r"^>\s?", line)]
        cleaned_text = "\n".join(cleaned).strip()
        if cleaned_text:
            return cleaned_text
    return body


def _is_greeting_pattern(body: str, pattern: str) -> bool:
    """Return True if *pattern* appears as part of a greeting/salutation.

    A greeting is detected when:
    1. The pattern occurs within the first 200 characters of the body, AND
    2. Within 100 characters after the pattern, '様' or '御中' appears.

    This distinguishes greetings like '株式会社finn\\n永田様' from echo-back
    lines like '会社名: 株式会社finn' where no honorific follows.
    """
    idx = body.lower().find(pattern.lower())
    if idx == -1 or idx > 200:
        return False
    after = body[idx + len(pattern): idx + len(pattern) + 100]
    return "様" in after or "御中" in after or "さま" in after or "お世話になっております" in after or "お世話になります" in after


def _is_form_echoback(body: str, pattern: str) -> bool:
    """Return True if pattern appears as part of form field echo-back.

    Detects patterns like '社名:株式会社finn' or 'メールアドレス service@finn.co.jp'
    where a form field label appears within 30 characters before the pattern.
    """
    labels = ["社名", "会社名", "企業名", "メールアドレス", "email", "e-mail", "mail"]
    idx = body.lower().find(pattern.lower())
    while idx != -1:
        # Check up to 30 chars before the pattern for a form label
        start = max(0, idx - 30)
        before = body[start:idx].lower()
        for label in labels:
            if label.lower() in before:
                return True
        # Search for next occurrence
        idx = body.lower().find(pattern.lower(), idx + 1)
    return False


def filter_noise(emails: list, settings: dict) -> list:
    """Filter noisy emails based on configured patterns.

    Args:
        emails: List of Email objects to filter.
        settings: The ``noise_filter`` section of settings.yaml.

    Returns:
        List of Email objects that are not classified as noise.
    """
    auto_reply_patterns: list[str] = settings.get("auto_reply_patterns", [])
    newsletter_patterns: list[str] = settings.get("newsletter_patterns", [])
    bounce_patterns: list[str] = settings.get("bounce_patterns", [])
    auto_confirm_body_patterns: list[str] = settings.get("auto_confirm_body_patterns", [])
    auto_confirm_min_matches: int = settings.get("auto_confirm_min_matches", 0)
    self_company: dict = settings.get("self_company", {})
    sender_domains: list[str] = self_company.get("sender_domains", [])
    body_identity_patterns: list[str] = self_company.get("body_identity_patterns", [])

    filtered: list = []

    for email in emails:
        reason = _classify_noise(
            email,
            auto_reply_patterns,
            newsletter_patterns,
            bounce_patterns,
            auto_confirm_body_patterns,
            auto_confirm_min_matches,
            sender_domains,
            body_identity_patterns,
        )

        if reason is not None:
            logger.info(
                "Excluded email id=%s subject=%r reason=%s",
                email.id,
                email.subject,
                reason,
            )
        else:
            filtered.append(email)

    return filtered


def _classify_noise(
    email,
    auto_reply_patterns: list[str],
    newsletter_patterns: list[str],
    bounce_patterns: list[str],
    auto_confirm_body_patterns: list[str],
    auto_confirm_min_matches: int,
    sender_domains: list[str] = [],
    body_identity_patterns: list[str] = [],
) -> Optional[str]:
    """Return a reason string if the email is noise, otherwise None."""
    sender_lower = email.sender.lower()
    subject_lower = email.subject.lower()
    body_lower = email.body.lower()
    stripped_body = _strip_quoted_reply(email.body)
    stripped_body_lower = stripped_body.lower()

    # 0a. Self-company sender: domain matches sender_domains
    sender_domain = _extract_sender_domain(email.sender)
    for domain in sender_domains:
        if sender_domain == domain.lower():
            return f"self_company_sender (domain={domain!r})"

    # 0b. Self-company body: body contains identity patterns (checked on
    #     stripped body so that quoted replies don't trigger false positives).
    for pattern in body_identity_patterns:
        if pattern.lower() in stripped_body_lower:
            if not _is_greeting_pattern(stripped_body, pattern):
                if not _is_form_echoback(stripped_body, pattern):
                    return f"self_company_body (pattern={pattern!r})"

    # 1. Auto-reply: sender or subject matches any auto_reply_pattern
    for pattern in auto_reply_patterns:
        p = pattern.lower()
        if p in sender_lower or p in subject_lower:
            return f"auto_reply (pattern={pattern!r})"

    # 2. Newsletter: body matches any newsletter_pattern
    for pattern in newsletter_patterns:
        p = pattern.lower()
        if p in body_lower:
            return f"newsletter (pattern={pattern!r})"

    # 3. Bounce: subject matches any bounce_pattern
    for pattern in bounce_patterns:
        p = pattern.lower()
        if p in subject_lower:
            return f"bounce (pattern={pattern!r})"

    # 4. Auto-confirm: body matches multiple auto_confirm patterns
    #    (checked on stripped body to ignore quoted content).
    if auto_confirm_body_patterns and auto_confirm_min_matches > 0:
        match_count = sum(
            1 for pattern in auto_confirm_body_patterns
            if pattern.lower() in stripped_body_lower
        )
        if match_count >= auto_confirm_min_matches:
            return f"auto_confirm (matched {match_count} patterns)"

    return None
