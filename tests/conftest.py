"""Shared pytest fixtures for the Inquiry-lead-hunter test suite."""

import pytest

from inquiry_lead_hunter.models import Email


# ---------------------------------------------------------------------------
# Settings fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def settings() -> dict:
    """Return a settings dict equivalent to the contents of settings.yaml."""
    return {
        "noise_filter": {
            "auto_reply_patterns": [
                "auto-reply",
                "out of office",
                "noreply",
                "no-reply",
                "automatic reply",
            ],
            "newsletter_patterns": [
                "unsubscribe",
                "配信停止",
                "メールマガジン",
                "newsletter",
                "opt-out",
            ],
            "bounce_patterns": [
                "delivery failed",
                "mail delivery failure",
                "undeliverable",
                "mailer-daemon",
            ],
        },
        "keyword_filter": {
            "high_keywords": [
                "導入を検討",
                "見積もり",
                "デモ",
                "pricing",
                "quote",
                "demo request",
            ],
            "medium_keywords": [
                "興味があります",
                "詳細を教えて",
                "資料請求",
                "interested",
                "more information",
            ],
            "negative_keywords": [
                "採用",
                "就活",
                "インターン",
                "job",
                "career",
            ],
        },
        "keyword_weights": {
            "high": 30,
            "medium": 15,
        },
        "scoring": {
            "llm_threshold": 50,
            "notification_threshold": 60,
        },
    }


# ---------------------------------------------------------------------------
# Email sample fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def normal_email() -> Email:
    """A plain inquiry email that should pass all filters."""
    return Email(
        id="email-001",
        thread_id="thread-001",
        sender="prospect@example.com",
        subject="製品について問い合わせ",
        body="御社の製品について詳細を教えてください。導入を検討しており、見積もりをお願いしたいです。",
        received_at="2026-03-13T09:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def high_keyword_email() -> Email:
    """An email that contains one high-priority keyword."""
    return Email(
        id="email-002",
        thread_id="thread-002",
        sender="client@bigcorp.com",
        subject="デモのお願い",
        body="御社サービスのデモを見せていただけますか？",
        received_at="2026-03-13T10:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def high_and_medium_email() -> Email:
    """An email containing one high keyword and one medium keyword."""
    return Email(
        id="email-003",
        thread_id="thread-003",
        sender="user@startup.io",
        subject="詳細を教えてください",
        body="御社の pricing について興味があります。詳細を教えてください。",
        received_at="2026-03-13T11:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def two_high_keywords_email() -> Email:
    """An email with two distinct high-priority keywords (score >= 60)."""
    return Email(
        id="email-004",
        thread_id="thread-004",
        sender="vp@enterprise.co",
        subject="見積もりとデモをお願いしたい",
        body="見積もりをいただけますか。あわせてデモも希望します。",
        received_at="2026-03-13T12:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def medium_only_email() -> Email:
    """An email with only medium keywords — score 15, below threshold 50."""
    return Email(
        id="email-005",
        thread_id="thread-005",
        sender="curious@example.net",
        subject="資料請求",
        body="資料請求したいのですが、送っていただけますか？",
        received_at="2026-03-13T13:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def negative_keyword_email() -> Email:
    """An email containing a negative keyword that zeroes out the score."""
    return Email(
        id="email-006",
        thread_id="thread-006",
        sender="jobseeker@example.com",
        subject="採用についてお聞きしたい",
        body="御社の採用情報について詳細を教えてください。導入を検討しています。",
        received_at="2026-03-13T14:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def auto_reply_subject_email() -> Email:
    """An auto-reply detected via the subject line."""
    return Email(
        id="email-007",
        thread_id="thread-007",
        sender="someone@example.com",
        subject="Auto-Reply: Re: your inquiry",
        body="I am currently out of the office and will reply upon my return.",
        received_at="2026-03-13T08:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def auto_reply_sender_email() -> Email:
    """An auto-reply detected via the sender address."""
    return Email(
        id="email-008",
        thread_id="thread-008",
        sender="noreply@notifications.example.com",
        subject="Your account activity",
        body="Please do not reply to this email.",
        received_at="2026-03-13T08:10:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def newsletter_email() -> Email:
    """A newsletter email containing an unsubscribe link in the body."""
    return Email(
        id="email-009",
        thread_id="thread-009",
        sender="news@marketing.example.com",
        subject="今月のニュースレター",
        body="今月の特集記事をお届けします。配信停止はこちらからどうぞ。",
        received_at="2026-03-13T07:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def bounce_email() -> Email:
    """A bounce / delivery-failure notification."""
    return Email(
        id="email-010",
        thread_id="thread-010",
        sender="mailer-daemon@mail.example.com",
        subject="Mail Delivery Failure: your message to foo@bar.com",
        body="Your message could not be delivered.",
        received_at="2026-03-13T06:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def mixed_email_list(
    normal_email,
    auto_reply_subject_email,
    newsletter_email,
    bounce_email,
) -> list:
    """A list containing one clean email and three noisy emails."""
    return [normal_email, auto_reply_subject_email, newsletter_email, bounce_email]
