"""Keyword filter: scores emails by keyword matches and applies LLM threshold."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inquiry_lead_hunter.models import Email, ScoredEmail

logger = logging.getLogger(__name__)


def filter_by_keywords(emails: list, settings: dict) -> list:
    """Score emails by keyword matches and return those meeting the LLM threshold.

    Args:
        emails: List of Email objects to evaluate.
        settings: The full settings dict (must contain ``keyword_filter`` and
                  ``scoring`` sections).

    Returns:
        List of ScoredEmail objects whose keyword_score >= scoring.llm_threshold.
    """
    # Lazily import to avoid circular imports at module load time
    from inquiry_lead_hunter.models import ScoredEmail  # noqa: PLC0415

    kf_settings: dict = settings.get("keyword_filter", {})
    scoring_settings: dict = settings.get("scoring", {})

    high_keywords: list[str] = kf_settings.get("high_keywords", [])
    medium_keywords: list[str] = kf_settings.get("medium_keywords", [])
    negative_keywords: list[str] = kf_settings.get("negative_keywords", [])

    weights: dict = settings.get("keyword_weights", {})
    high_weight: int = weights.get("high", 30)
    medium_weight: int = weights.get("medium", 15)

    llm_threshold: int = scoring_settings.get("llm_threshold", 50)

    results: list = []

    for email in emails:
        scored = _score_email(
            email,
            high_keywords,
            medium_keywords,
            negative_keywords,
            high_weight,
            medium_weight,
        )

        logger.debug(
            "Scored email id=%s subject=%r score=%d matched=%r",
            email.id,
            email.subject,
            scored.keyword_score,
            scored.matched_keywords,
        )

        if scored.keyword_score >= llm_threshold:
            results.append(scored)
        else:
            logger.debug(
                "Excluded email id=%s score=%d (threshold=%d)",
                email.id,
                scored.keyword_score,
                llm_threshold,
            )

    return results


def _score_email(
    email,
    high_keywords: list[str],
    medium_keywords: list[str],
    negative_keywords: list[str],
    high_weight: int,
    medium_weight: int,
):
    """Compute keyword score for a single email."""
    from inquiry_lead_hunter.models import ScoredEmail  # noqa: PLC0415

    text = (email.subject + " " + email.body).lower()

    score = 0
    matched: list[str] = []

    # Collect unique matching high keywords
    for kw in high_keywords:
        if kw.lower() in text and kw not in matched:
            score += high_weight
            matched.append(kw)

    # Collect unique matching medium keywords
    for kw in medium_keywords:
        if kw.lower() in text and kw not in matched:
            score += medium_weight
            matched.append(kw)

    # Negative keyword: reset score to 0 if any match
    for kw in negative_keywords:
        if kw.lower() in text:
            score = 0
            if kw not in matched:
                matched.append(kw)
            break  # one negative match is enough to zero out

    return ScoredEmail(
        email=email,
        keyword_score=score,
        matched_keywords=matched,
    )
