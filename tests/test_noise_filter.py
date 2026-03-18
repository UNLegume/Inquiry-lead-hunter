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

    # ------------------------------------------------------------------
    # 10. Self-company sender emails are excluded
    # ------------------------------------------------------------------

    def test_self_company_sender_excluded(self, self_sent_outbound_email, settings):
        """finn.co.jpドメインからのメールが除外される。"""
        result = filter_noise([self_sent_outbound_email], settings["noise_filter"])
        assert result == []

    def test_self_company_sender_display_name_excluded(self, settings):
        """Display name形式のfinn.co.jpメールも除外される。"""
        email = Email(
            id="self-display",
            thread_id="t-self-display",
            sender="久野太郎 <kuno@finn.co.jp>",
            subject="SESパートナー提携のご提案",
            body="突然のご連絡失礼いたします。",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert result == []

    # ------------------------------------------------------------------
    # 11. Self-company body echoback emails are excluded
    # ------------------------------------------------------------------

    def test_self_company_body_echoback_excluded(
        self, self_sent_echoback_email, settings
    ):
        """本文に自社情報を含むエコーバックが除外される。"""
        result = filter_noise([self_sent_echoback_email], settings["noise_filter"])
        assert result == []

    def test_self_company_body_no_match_passes(self, settings):
        """自社情報を含まないメールは通過する。"""
        email = Email(
            id="no-self",
            thread_id="t-no-self",
            sender="info@other-company.co.jp",
            subject="お問い合わせ",
            body="弊社サービスについてご案内いたします。",
            received_at="2026-03-13T00:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert len(result) == 1

    # ------------------------------------------------------------------
    # 12. Empty self_company config doesn't break
    # ------------------------------------------------------------------

    def test_self_company_empty_config_passes(self, normal_email, settings):
        """self_company設定なしでもエラーにならない。"""
        no_self_settings = dict(settings["noise_filter"])
        no_self_settings.pop("self_company", None)
        result = filter_noise([normal_email], no_self_settings)
        assert len(result) == 1

    # ------------------------------------------------------------------
    # 13. New partnership proposals pass through (regression)
    # ------------------------------------------------------------------

    def test_new_partnership_not_excluded(
        self, new_partnership_proposal_email, settings
    ):
        """新規協業提案メールは除外されずに通過する。"""
        result = filter_noise(
            [new_partnership_proposal_email], settings["noise_filter"]
        )
        assert len(result) == 1
        assert result[0].id == "email-new-partner"

    # ------------------------------------------------------------------
    # 14. Reply emails with quoted self-company info pass through
    # ------------------------------------------------------------------

    def test_reply_with_quoted_self_company_passes(
        self, reply_email_with_quoted_self_company, settings
    ):
        """引用部に自社情報を含む返信メールがリードとして通過する。"""
        result = filter_noise(
            [reply_email_with_quoted_self_company], settings["noise_filter"]
        )
        assert len(result) == 1
        assert result[0].id == "email-reply-quoted-self"

    def test_reply_with_auto_confirm_in_quote_passes(
        self, reply_email_with_auto_confirm_in_quote, settings
    ):
        """引用部にauto_confirmパターンを含む返信メールが通過する。"""
        result = filter_noise(
            [reply_email_with_auto_confirm_in_quote], settings["noise_filter"]
        )
        assert len(result) == 1
        assert result[0].id == "email-reply-ac-quote"

    def test_greeting_with_hiragana_sama_passes(self, settings):
        """「さま」（ひらがな）で宛名の返信メールが通過する。"""
        email = Email(
            id="email-hiragana-sama",
            thread_id="thread-hiragana-sama",
            sender="support@kj-partners.co.jp",
            subject="Re: ホームページのお問い合わせ",
            body=(
                "株式会社finn 久野聡一郎さま\n\n"
                "お世話になっております。\n"
                "教育情報パートナーズ株式会社の中村でございます。\n\n"
                "協業のご依頼ありがとうございます。\n"
                "一度、お話させていただきたく存じます。\n"
            ),
            received_at="2026-03-13T10:00:00Z",
            labels=["INBOX"],
        )
        result = filter_noise([email], settings["noise_filter"])
        assert len(result) == 1
        assert result[0].id == "email-hiragana-sama"

    def test_greeting_without_honorific_passes(self, settings):
        """敬称なしの宛名でも返信メールが通過する。"""
        email = Email(
            id="email-no-honorific",
            thread_id="thread-no-honorific",
            sender="motohashi@gigooo.com",
            subject="HPからお問い合わせありがとうございました",
            body=(
                "株式会社finn\n\n"
                "お世話になります。ギグー本橋です。\n"
                "ご協業に関してご連絡ありがとうございます。\n\n"
                "是非、お打合せを宜しくお願いいたします。\n"
            ),
            received_at="2026-03-13T11:00:00Z",
            labels=["INBOX"],
        )
        result = filter_noise([email], settings["noise_filter"])
        assert len(result) == 1
        assert result[0].id == "email-no-honorific"

    def test_external_reply_with_finn_in_outlook_quote_passes(self, settings):
        """Outlook形式引用内にfinn情報がある外部返信メールが通過する。"""
        email = Email(
            id="email-outlook-quote",
            thread_id="thread-outlook-quote",
            sender="tanaka@external-corp.co.jp",
            subject="Re: SESパートナー提携のご提案",
            body=(
                "永田様\n\n"
                "ご連絡ありがとうございます。\n"
                "ぜひお打ち合わせさせてください。\n\n"
                "From: 永田修大 <service@finn.co.jp>\n"
                "Sent: Monday, March 15, 2026\n"
                "Subject: SESパートナー提携のご提案\n\n"
                "> 突然のご連絡失礼いたします。\n"
                "> 株式会社finnでCPOを務めております永田と申します。\n"
            ),
            received_at="2026-03-16T10:00:00Z",
            labels=["INBOX"],
        )
        result = filter_noise([email], settings["noise_filter"])
        assert len(result) == 1
        assert result[0].id == "email-outlook-quote"

    def test_external_reply_with_finn_in_emdash_quote_passes(self, settings):
        email = Email(
            id="emdash-quote",
            thread_id="t-emdash-quote",
            sender="uehara@maplesystems.co.jp",
            subject="Re:お問い合わせの御礼",
            body="finn 永田様\n\nお世話になっております。\n協業について前向きに検討させていただきます。\n\n────────────────\n株式会社finnでCPOを務めております永田です。\nSES協業のご提案をさせていただきたく...",
            received_at="2026-03-18T10:00:00Z",
        )
        result = filter_noise([email], settings["noise_filter"])
        assert len(result) == 1

    def test_form_echoback_with_company_name_passes(self, settings):
        """エコーバック内「社名:株式会社finn」がself_company_bodyをスキップする。"""
        email = Email(
            id="email-form-echo-pass",
            thread_id="thread-form-echo-pass",
            sender="info@formservice.co.jp",
            subject="お問い合わせを受け付けました",
            body=(
                "以下の内容でお問い合わせを受け付けました。\n\n"
                "社名: 株式会社finn\n"
                "メールアドレス: service@finn.co.jp\n"
                "お問い合わせ内容: SES事業についてのご提案\n"
            ),
            received_at="2026-03-16T11:00:00Z",
            labels=["INBOX"],
        )
        result = filter_noise([email], settings["noise_filter"])
        # self_company_body はスキップされるが、auto_confirm で除外される可能性あり
        # このテストでは self_company_body で除外されないことを確認
        from inquiry_lead_hunter.noise_filter import _classify_noise
        reason = _classify_noise(
            email,
            settings["noise_filter"]["auto_reply_patterns"],
            settings["noise_filter"]["newsletter_patterns"],
            settings["noise_filter"]["bounce_patterns"],
            [],  # auto_confirm_body_patterns を空にして self_company_body のみテスト
            0,
            settings["noise_filter"]["self_company"]["sender_domains"],
            settings["noise_filter"]["self_company"]["body_identity_patterns"],
        )
        assert reason is None


class TestStripQuotedReply:
    """Unit tests for _strip_quoted_reply helper."""

    def test_japanese_gmail_marker(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "新規テキスト\n\n2024年3月15日(金) 10:30 user@example.com:\n> 引用"
        assert _strip_quoted_reply(body) == "新規テキスト"

    def test_english_gmail_marker(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "New text here\n\nOn Mon, Mar 15, 2024 at 10:30 AM user@example.com wrote:\n> quoted"
        assert _strip_quoted_reply(body) == "New text here"

    def test_outlook_marker(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "新規本文\n\n--- Original Message ---\nFrom: user@example.com"
        assert _strip_quoted_reply(body) == "新規本文"

    def test_no_marker_returns_original(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "普通のメール本文です。"
        assert _strip_quoted_reply(body) == body

    def test_empty_string(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        assert _strip_quoted_reply("") == ""

    def test_marker_at_beginning_returns_original(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "2024年3月15日(金) 10:30 user@example.com:\n> 全て引用"
        assert _strip_quoted_reply(body) == body

    def test_outlook_from_header(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = (
            "ご連絡ありがとうございます。\n\n"
            "From: 永田修大 <nobuhiro-nagata.hojicha@finn.co.jp>\n"
            "Sent: Monday, March 15, 2026\n"
            "Subject: SESパートナー提携のご提案\n\n"
            "> 株式会社finnの永田です。\n"
        )
        assert _strip_quoted_reply(body) == "ご連絡ありがとうございます。"

    def test_japanese_sender_header(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = (
            "お打ち合わせ可能です。\n\n"
            "差出人: 永田修大\n"
            "送信日時: 2026年3月15日\n"
            "> 株式会社finnの永田です。\n"
        )
        assert _strip_quoted_reply(body) == "お打ち合わせ可能です。"

    def test_underscore_separator(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = (
            "ご提案ありがとうございます。\n\n"
            "________________________________\n"
            "From: service@finn.co.jp\n"
            "Subject: お問い合わせ\n"
        )
        assert _strip_quoted_reply(body) == "ご提案ありがとうございます。"

    def test_em_dash_separator(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "ご連絡ありがとうございます。\n\n────────────────\n株式会社finnでCPOを務めております。"
        result = _strip_quoted_reply(body)
        assert "株式会社finn" not in result
        assert "ご連絡ありがとうございます" in result

    def test_gt_prefix_with_date_header(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "ぜひ協業させてください。\n\n> 2026/02/19 22:00、contact@example.comのメール:\n>\n> company : 株式会社finn"
        result = _strip_quoted_reply(body)
        assert "株式会社finn" not in result
        assert "ぜひ協業させてください" in result

    def test_gt_prefix_lines_removed(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "承知しました。\n\n> お問い合わせ内容\n> 株式会社finnのCOOです\n> よろしくお願いします"
        result = _strip_quoted_reply(body)
        assert "株式会社finn" not in result
        assert "承知しました" in result

    def test_on_date_without_wrote(self):
        from inquiry_lead_hunter.noise_filter import _strip_quoted_reply

        body = "以上よろしくお願いいたします。\nOn Thu, 5 Mar 2026 05:25:37 +0000\n久野聡一郎 <service@finn.co.jp>殿から頂いた"
        result = _strip_quoted_reply(body)
        assert "service@finn.co.jp" not in result
        assert "よろしくお願いいたします" in result


class TestIsGreetingPattern:
    """Unit tests for _is_greeting_pattern helper."""

    def test_greeting_with_sama(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "株式会社finn\n永田様\n\nお世話になっております。"
        assert _is_greeting_pattern(body, "株式会社finn") is True

    def test_greeting_with_onchu(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "株式会社finn御中\n\nお世話になっております。"
        assert _is_greeting_pattern(body, "株式会社finn") is True

    def test_echoback_not_greeting(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "会社名: 株式会社finn\nメール: service@finn.co.jp\n内容: ご提案"
        assert _is_greeting_pattern(body, "株式会社finn") is False

    def test_pattern_not_found(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "お世話になっております。田中です。"
        assert _is_greeting_pattern(body, "株式会社finn") is False

    def test_pattern_beyond_200_chars(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "あ" * 201 + "株式会社finn\n永田様"
        assert _is_greeting_pattern(body, "株式会社finn") is False

    def test_greeting_with_hiragana_sama(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "株式会社finn 久野聡一郎さま\n\nお世話になっております。"
        assert _is_greeting_pattern(body, "株式会社finn") is True

    def test_greeting_without_honorific(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "株式会社finn\n\nお世話になります。ギグー本橋です。"
        assert _is_greeting_pattern(body, "株式会社finn") is True

    def test_greeting_with_osewa_ni_natte_orimasu(self):
        from inquiry_lead_hunter.noise_filter import _is_greeting_pattern

        body = "株式会社finn\n\nお世話になっております。田中です。"
        assert _is_greeting_pattern(body, "株式会社finn") is True


class TestIsFormEchoback:
    """Unit tests for _is_form_echoback helper."""

    def test_company_name_after_label(self):
        from inquiry_lead_hunter.noise_filter import _is_form_echoback

        body = "社名:株式会社finn\nメール: test@example.com"
        assert _is_form_echoback(body, "株式会社finn") is True

    def test_email_after_label(self):
        from inquiry_lead_hunter.noise_filter import _is_form_echoback

        body = "メールアドレス service@finn.co.jp\n内容: ご提案"
        assert _is_form_echoback(body, "service@finn.co.jp") is True

    def test_no_label_before_pattern(self):
        from inquiry_lead_hunter.noise_filter import _is_form_echoback

        body = "株式会社finnの永田です。"
        assert _is_form_echoback(body, "株式会社finn") is False

    def test_pattern_in_regular_text(self):
        from inquiry_lead_hunter.noise_filter import _is_form_echoback

        body = "突然のご連絡失礼いたします。株式会社finnでCPOを務めております。"
        assert _is_form_echoback(body, "株式会社finn") is False
