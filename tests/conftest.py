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
            "auto_confirm_body_patterns": [
                "承りました",
                "受け付けました",
                "受け付けいたしました",
                "受付いたしました",
                "お問い合わせを受け付け",
                "お問い合わせを承り",
                "担当者より",
                "担当より",
                "担当者から",
                "営業日以内",
                "折り返し",
                "自動返信",
                "自動配信",
                "自動送信",
                "内容は以下",
                "以下のとおりです",
                "以下の通りです",
                "以下にて承り",
                "ご入力いただきました内容",
                "ご送信内容",
                "送信されました",
                "内容を確認",
                "お問い合わせ内容の確認",
                "以下の内容で受け付け",
                "以下の内容でお問い合わせ",
                "心当たりがない場合",
                "このメールは送信専用",
                "送信専用のメールアドレス",
                "このメールに返信しないで",
                "このメールへの返信はできません",
                "返信いただけません",
                "お問い合わせフォーム",
                "受付番号",
            ],
            "auto_confirm_min_matches": 2,
            "self_company": {
                "sender_domains": ["finn.co.jp"],
                "body_identity_patterns": ["株式会社finn", "service@finn.co.jp"],
            },
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
def auto_confirm_email() -> Email:
    """受付確認メール（定型フレーズ3つ）— ノイズとして除外されるべき。"""
    return Email(
        id="email-011",
        thread_id="thread-011",
        sender="info@some-company.co.jp",
        subject="お問い合わせありがとうございます",
        body=(
            "お問い合わせいただきありがとうございます。\n"
            "以下の内容で受け付けいたしました。\n\n"
            "担当者より折り返しご連絡いたしますので、しばらくお待ちください。\n"
            "このメールは自動配信されています。\n"
        ),
        received_at="2026-03-13T09:30:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def human_reply_with_thanks_subject() -> Email:
    """件名に「ありがとうございます」を含むが人間の返信 — 通過すべき。"""
    return Email(
        id="email-012",
        thread_id="thread-012",
        sender="sato@sakuya.co.jp",
        subject="★お問合わせありがとうございます【サクヤ佐藤】★",
        body=(
            "お問い合わせいただきありがとうございます。\n"
            "ぜひ一度お打ち合わせさせてください。\n\n"
            "以下の日程でご都合いかがでしょうか。\n"
            "・3/18（火）14:00〜\n"
            "・3/19（水）10:00〜\n"
        ),
        received_at="2026-03-13T10:30:00Z",
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


@pytest.fixture()
def self_sent_echoback_email() -> Email:
    """自社フォーム送信のエコーバック — Fromは他社だが本文に自社情報あり。"""
    return Email(
        id="email-self-echo",
        thread_id="thread-self-echo",
        sender="info@other-company.co.jp",
        subject="お問い合わせありがとうございます",
        body=(
            "お問い合わせいただきありがとうございます。\n"
            "以下の内容でお問い合わせを受け付けました。\n\n"
            "会社名: 株式会社finn\n"
            "メール: service@finn.co.jp\n"
            "内容: SESパートナー提携のご提案\n"
        ),
        received_at="2026-03-13T11:00:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def self_sent_outbound_email() -> Email:
    """finn社員からクライアントへの送信メール。"""
    return Email(
        id="email-self-outbound",
        thread_id="thread-self-outbound",
        sender="kuno@finn.co.jp",
        subject="SESパートナー提携のご提案",
        body=(
            "突然のご連絡失礼いたします。\n"
            "株式会社finnの久野と申します。\n"
            "SESパートナー提携についてご提案させていただきたく...\n"
        ),
        received_at="2026-03-13T11:30:00Z",
        labels=["INBOX"],
    )


@pytest.fixture()
def new_partnership_proposal_email() -> Email:
    """外部企業からの新規協業提案 — リードとして通過すべき。"""
    return Email(
        id="email-new-partner",
        thread_id="thread-new-partner",
        sender="tanaka@external-corp.co.jp",
        subject="協業のご提案",
        body=(
            "初めてご連絡いたします。\n"
            "株式会社エクスターナルの田中と申します。\n"
            "貴社のSES事業について拝見し、ぜひ協業させていただきたくご連絡いたしました。\n"
            "一度お打ち合わせの機会をいただけますと幸いです。\n"
        ),
        received_at="2026-03-13T12:00:00Z",
        labels=["INBOX"],
    )
