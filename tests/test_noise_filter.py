"""Tests for noise_filter.filter_noise."""

import pytest

from inquiry_lead_hunter.models import Email
from inquiry_lead_hunter.noise_filter import filter_noise


class TestFilterNoise:
    """Unit tests for filter_noise()."""

    # ------------------------------------------------------------------
    # 1. Normal email passes through
    # ------------------------------------------------------------------

    def test_normal_email_passes(self, normal_email, settings):
        """A plain inquiry email must not be excluded."""
        result = filter_noise([normal_email], settings["noise_filter"])
        assert len(result) == 1
        assert result[0] is normal_email

    # ------------------------------------------------------------------
    # 2. Auto-reply emails are excluded
    # ------------------------------------------------------------------

    def test_auto_reply_subject_excluded(self, auto_reply_subject_email, settings):
        """An email whose subject contains an auto-reply pattern must be excluded."""
        result = filter_noise([auto_reply_subject_email], settings["noise_filter"])
        assert result == []

    def test_auto_reply_sender_excluded(self, auto_reply_sender_email, settings):
        """An email whose sender matches an auto-reply pattern must be excluded."""
        result = filter_noise([auto_reply_sender_email], settings["noise_filter"])
        assert result == []

    # ------------------------------------------------------------------
    # 3. Newsletter emails are excluded
    # ------------------------------------------------------------------

    def test_newsletter_body_excluded(self, newsletter_email, settings):
        """An email with a newsletter pattern in the body must be excluded."""
        result = filter_noise([newsletter_email], settings["noise_filter"])
        assert result == []

    def test_newsletter_english_unsubscribe_excluded(self, settings):
        """An email with 'unsubscribe' in the body must be excluded."""
        email = Email(
            id="nl-en",
            thread_id="t-nl-en",
            sender="news@example.com",
            subject="Monthly digest",
            body="Click here to unsubscribe from this mailing list.",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert result == []

    # ------------------------------------------------------------------
    # 4. Bounce emails are excluded
    # ------------------------------------------------------------------

    def test_bounce_email_excluded(self, bounce_email, settings):
        """An email whose subject contains a bounce pattern must be excluded."""
        result = filter_noise([bounce_email], settings["noise_filter"])
        assert result == []

    def test_undeliverable_subject_excluded(self, settings):
        """An email with 'undeliverable' in the subject must be excluded."""
        email = Email(
            id="bounce-2",
            thread_id="t-bounce-2",
            sender="postmaster@mail.example.com",
            subject="Undeliverable: hello",
            body="The message was not delivered.",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert result == []

    # ------------------------------------------------------------------
    # 5. Empty list input
    # ------------------------------------------------------------------

    def test_empty_list_returns_empty(self, settings):
        """Passing an empty list must return an empty list without error."""
        result = filter_noise([], settings["noise_filter"])
        assert result == []

    # ------------------------------------------------------------------
    # 6. Case-insensitive pattern matching
    # ------------------------------------------------------------------

    def test_auto_reply_case_insensitive_subject(self, settings):
        """Pattern matching in the subject must be case-insensitive."""
        email = Email(
            id="case-001",
            thread_id="t-case-001",
            sender="human@example.com",
            subject="AUTOMATIC REPLY: I am away",
            body="I will be back next week.",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert result == []

    def test_newsletter_case_insensitive_body(self, settings):
        """Pattern matching in the body must be case-insensitive."""
        email = Email(
            id="case-002",
            thread_id="t-case-002",
            sender="promo@example.com",
            subject="Special offer",
            body="To stop receiving emails, click UNSUBSCRIBE here.",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert result == []

    def test_bounce_case_insensitive_subject(self, settings):
        """Bounce pattern matching in the subject must be case-insensitive."""
        email = Email(
            id="case-003",
            thread_id="t-case-003",
            sender="postmaster@example.com",
            subject="DELIVERY FAILED: message to user@example.com",
            body="Could not deliver your message.",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert result == []

    # ------------------------------------------------------------------
    # 7. Mixed list: only noise is removed
    # ------------------------------------------------------------------

    def test_mixed_list_keeps_only_clean_emails(self, mixed_email_list, settings):
        """Only the clean email must survive when mixed with noisy ones."""
        result = filter_noise(mixed_email_list, settings["noise_filter"])
        assert len(result) == 1
        assert result[0].id == "email-001"

    # ------------------------------------------------------------------
    # 8. Multiple clean emails all pass
    # ------------------------------------------------------------------

    def test_multiple_clean_emails_all_pass(self, normal_email, settings):
        """When all emails are clean, all of them must be returned."""
        email2 = Email(
            id="clean-002",
            thread_id="t-clean-002",
            sender="another@example.com",
            subject="お見積もり依頼",
            body="見積もりをお願いします。",
            received_at="2026-03-13T10:00:00Z",
        )
        result = filter_noise([normal_email, email2], settings["noise_filter"])
        assert len(result) == 2

    # ------------------------------------------------------------------
    # 9. Auto-confirm emails are excluded
    # ------------------------------------------------------------------

    def test_auto_confirm_email_excluded(self, auto_confirm_email, settings):
        """受付確認メール（パターン2つ以上一致）は除外される。"""
        result = filter_noise([auto_confirm_email], settings["noise_filter"])
        assert result == []

    def test_auto_confirm_single_match_passes(self, settings):
        """パターンが1つだけ一致する場合は除外されない。"""
        email = Email(
            id="ac-single",
            thread_id="t-ac-single",
            sender="info@company.co.jp",
            subject="お問い合わせについて",
            body="折り返しご連絡をお待ちください。よろしくお願いいたします。",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert len(result) == 1

    def test_human_reply_with_thanks_subject_passes(
        self, human_reply_with_thanks_subject, settings
    ):
        """件名に「ありがとう」を含むが人間の返信は通過する。"""
        result = filter_noise(
            [human_reply_with_thanks_subject], settings["noise_filter"]
        )
        assert len(result) == 1
        assert result[0].id == "email-012"

    def test_auto_confirm_min_matches_respected(self, settings):
        """min_matches の値が正しく効く（3に変更するとパターン2つでは通過）。"""
        custom_settings = dict(settings["noise_filter"])
        custom_settings["auto_confirm_min_matches"] = 3
        email = Email(
            id="ac-threshold",
            thread_id="t-ac-threshold",
            sender="info@company.co.jp",
            subject="お問い合わせありがとうございます",
            body="お問い合わせありがとうございます。折り返しご連絡いたします。",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], custom_settings)
        assert len(result) == 1
