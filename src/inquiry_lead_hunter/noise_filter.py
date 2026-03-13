"""Noise filter: removes auto-replies, newsletters, and bounce messages."""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from inquiry_lead_hunter.models import Email

logger = logging.getLogger(__name__)


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

    filtered: list = []

    for email in emails:
        reason = _classify_noise(
            email,
            auto_reply_patterns,
            newsletter_patterns,
            bounce_patterns,
            auto_confirm_body_patterns,
            auto_confirm_min_matches,
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
) -> Optional[str]:
    """Return a reason string if the email is noise, otherwise None."""
    sender_lower = email.sender.lower()
    subject_lower = email.subject.lower()
    body_lower = email.body.lower()

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
    if auto_confirm_body_patterns and auto_confirm_min_matches > 0:
        match_count = sum(
            1 for pattern in auto_confirm_body_patterns
            if pattern.lower() in body_lower
        )
        if match_count >= auto_confirm_min_matches:
            return f"auto_confirm (matched {match_count} patterns)"

    return None
