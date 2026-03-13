"""Tests for inquiry_lead_hunter.main module."""

import sys
from unittest.mock import MagicMock, patch, call

import pytest

from inquiry_lead_hunter.models import Email, ScoredEmail
from inquiry_lead_hunter.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**kwargs) -> Config:
    defaults = dict(
        anthropic_api_key="test-api-key",
        gmail_credentials_path="/tmp/creds.json",
        gmail_delegated_user="user@example.com",
        slack_webhook_url="https://hooks.slack.com/test",
        settings={
            "noise_filter": {},
            "gmail": {
                "label_inquiry": "問い合わせ",
                "label_processed": "処理済",
                "max_results": 50,
            },
        },
        prompts={},
    )
    defaults.update(kwargs)
    return Config(**defaults)


def _make_email(id: str = "email-001") -> Email:
    return Email(
        id=id,
        thread_id=f"thread-{id}",
        sender="test@example.com",
        subject="テスト件名",
        body="テスト本文",
        received_at="2026-03-13T09:00:00Z",
        labels=["INBOX"],
    )


def _make_scored(email: Email, llm_score: int = 70) -> ScoredEmail:
    return ScoredEmail(
        email=email,
        keyword_score=30,
        llm_score=llm_score,
        category="inquiry",
        reason="テスト理由",
        matched_keywords=["デモ"],
    )


# ---------------------------------------------------------------------------
# Test: normal flow
# ---------------------------------------------------------------------------

@patch("inquiry_lead_hunter.main.notify")
@patch("inquiry_lead_hunter.main.score_emails")
@patch("inquiry_lead_hunter.main.filter_by_keywords")
@patch("inquiry_lead_hunter.main.filter_noise")
@patch("inquiry_lead_hunter.main.mark_as_processed")
@patch("inquiry_lead_hunter.main.fetch_inquiry_emails")
@patch("inquiry_lead_hunter.main.get_gmail_service")
@patch("inquiry_lead_hunter.main.load_config")
def test_normal_flow(
    mock_load_config,
    mock_get_gmail_service,
    mock_fetch_inquiry_emails,
    mock_mark_as_processed,
    mock_filter_noise,
    mock_filter_by_keywords,
    mock_score_emails,
    mock_notify,
):
    """正常フロー: 各ステップが正しい順序・引数で呼ばれる"""
    config = _make_config()
    mock_load_config.return_value = config

    service = MagicMock()
    mock_get_gmail_service.return_value = service

    email1 = _make_email("email-001")
    email2 = _make_email("email-002")
    emails = [email1, email2]
    # 1回目はメールあり、2回目は空リストでループ終了
    mock_fetch_inquiry_emails.side_effect = [emails, []]

    # ノイズ除外後は email1 のみ残る
    mock_filter_noise.return_value = [email1]

    # キーワードフィルタ結果 (llm_score は score_emails 呼び出し後に設定される想定)
    candidate = ScoredEmail(email=email1, keyword_score=30)
    mock_filter_by_keywords.return_value = [candidate]

    # LLMスコアリング後: score_emails が candidate の llm_score を設定してから返す
    def _side_effect_score(candidates, cfg):
        # score_emails の副作用として llm_score を設定
        for c in candidates:
            c.llm_score = 70
            c.category = "inquiry"
            c.reason = "テスト理由"
        return [_make_scored(candidates[0].email, llm_score=70)]

    mock_score_emails.side_effect = _side_effect_score

    from inquiry_lead_hunter.main import run
    run()

    # 各関数が呼ばれたことを確認
    mock_load_config.assert_called_once()
    mock_get_gmail_service.assert_called_once_with(
        config.gmail_credentials_path,
        config.gmail_delegated_user,
    )
    # fetch_inquiry_emails は2回呼ばれる（1回目: データあり、2回目: 空でループ終了）
    assert mock_fetch_inquiry_emails.call_count == 2
    mock_fetch_inquiry_emails.assert_called_with(service, config.settings)
    mock_filter_noise.assert_called_once_with(emails, config.settings["noise_filter"])
    mock_filter_by_keywords.assert_called_once_with([email1], config.settings)
    mock_score_emails.assert_called_once_with([candidate], config)

    # mark_as_processed: LLMエラーなし(llm_scoreが設定済み) → 全メールIDが渡される
    mock_mark_as_processed.assert_called_once_with(
        service,
        ["email-001", "email-002"],
        config.settings,
    )

    # Slack通知: score_emails が返した ScoredEmail で通知
    assert mock_notify.called
    assert mock_notify.call_args[0][1] == config.slack_webhook_url


# ---------------------------------------------------------------------------
# Test: no emails
# ---------------------------------------------------------------------------

@patch("inquiry_lead_hunter.main.filter_noise")
@patch("inquiry_lead_hunter.main.fetch_inquiry_emails")
@patch("inquiry_lead_hunter.main.get_gmail_service")
@patch("inquiry_lead_hunter.main.load_config")
def test_no_emails_early_return(
    mock_load_config,
    mock_get_gmail_service,
    mock_fetch_inquiry_emails,
    mock_filter_noise,
):
    """メールなしの場合: 早期リターンしノイズ除外以降は呼ばれない"""
    mock_load_config.return_value = _make_config()
    mock_get_gmail_service.return_value = MagicMock()
    mock_fetch_inquiry_emails.return_value = []

    from inquiry_lead_hunter.main import run
    run()

    mock_filter_noise.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Gmail authentication error → sys.exit(1) + Slack error notification
# ---------------------------------------------------------------------------

@patch("inquiry_lead_hunter.main.notify_error")
@patch("inquiry_lead_hunter.main.get_gmail_service")
@patch("inquiry_lead_hunter.main.load_config")
def test_gmail_auth_error_exits_with_1(
    mock_load_config,
    mock_get_gmail_service,
    mock_notify_error,
):
    """Gmail認証エラー: sys.exit(1) が呼ばれ、Slackにエラー通知される"""
    config = _make_config()
    mock_load_config.return_value = config
    mock_get_gmail_service.side_effect = Exception("認証に失敗しました")

    from inquiry_lead_hunter.main import run

    with pytest.raises(SystemExit) as exc_info:
        run()

    assert exc_info.value.code == 1
    mock_notify_error.assert_called_once_with(
        "認証に失敗しました",
        config.slack_webhook_url,
    )


# ---------------------------------------------------------------------------
# Test: LLM error → that email is NOT marked as processed
# ---------------------------------------------------------------------------

@patch("inquiry_lead_hunter.main.notify")
@patch("inquiry_lead_hunter.main.score_emails")
@patch("inquiry_lead_hunter.main.filter_by_keywords")
@patch("inquiry_lead_hunter.main.filter_noise")
@patch("inquiry_lead_hunter.main.mark_as_processed")
@patch("inquiry_lead_hunter.main.fetch_inquiry_emails")
@patch("inquiry_lead_hunter.main.get_gmail_service")
@patch("inquiry_lead_hunter.main.load_config")
def test_llm_error_email_not_marked(
    mock_load_config,
    mock_get_gmail_service,
    mock_fetch_inquiry_emails,
    mock_mark_as_processed,
    mock_filter_noise,
    mock_filter_by_keywords,
    mock_score_emails,
    mock_notify,
):
    """LLMエラーのメール(llm_score=None)は処理済ラベルが付かない"""
    config = _make_config()
    mock_load_config.return_value = config
    mock_get_gmail_service.return_value = MagicMock()

    email_ok = _make_email("email-ok")
    email_err = _make_email("email-err")
    # 1回目はメールあり、2回目は空リストでループ終了
    mock_fetch_inquiry_emails.side_effect = [[email_ok, email_err], []]
    mock_filter_noise.return_value = [email_ok, email_err]

    # email_err は llm_score=None (LLMエラー)
    candidate_ok = ScoredEmail(email=email_ok, keyword_score=30)
    candidate_err = ScoredEmail(email=email_err, keyword_score=30)
    mock_filter_by_keywords.return_value = [candidate_ok, candidate_err]

    # score_emails 後: email_ok のみスコアあり、email_err はエラーで llm_score=None のまま
    def _side_effect_score_partial(candidates, cfg):
        # candidate_ok のみ llm_score を設定、candidate_err はエラー扱いで None のまま
        candidate_ok.llm_score = 70
        scored_ok = _make_scored(email_ok, llm_score=70)
        return [scored_ok]

    mock_score_emails.side_effect = _side_effect_score_partial

    from inquiry_lead_hunter.main import run
    run()

    # email_err の llm_score は None なので ids_to_mark から除外される
    call_args = mock_mark_as_processed.call_args
    marked_ids = call_args[0][1]
    assert "email-err" not in marked_ids
    assert "email-ok" in marked_ids


# ---------------------------------------------------------------------------
# Test: all emails are noise → keyword filter receives empty list
# ---------------------------------------------------------------------------

@patch("inquiry_lead_hunter.main.notify")
@patch("inquiry_lead_hunter.main.score_emails")
@patch("inquiry_lead_hunter.main.filter_by_keywords")
@patch("inquiry_lead_hunter.main.filter_noise")
@patch("inquiry_lead_hunter.main.mark_as_processed")
@patch("inquiry_lead_hunter.main.fetch_inquiry_emails")
@patch("inquiry_lead_hunter.main.get_gmail_service")
@patch("inquiry_lead_hunter.main.load_config")
def test_all_noise_empty_list_to_keyword_filter(
    mock_load_config,
    mock_get_gmail_service,
    mock_fetch_inquiry_emails,
    mock_mark_as_processed,
    mock_filter_noise,
    mock_filter_by_keywords,
    mock_score_emails,
    mock_notify,
):
    """全てノイズの場合: キーワードフィルタに空リストが渡される"""
    config = _make_config()
    mock_load_config.return_value = config
    mock_get_gmail_service.return_value = MagicMock()

    email1 = _make_email("email-noise-1")
    email2 = _make_email("email-noise-2")
    # 1回目はメールあり、2回目は空でループ終了
    mock_fetch_inquiry_emails.side_effect = [[email1, email2], []]

    # 全てノイズとして除外
    mock_filter_noise.return_value = []
    mock_filter_by_keywords.return_value = []
    mock_score_emails.return_value = []

    from inquiry_lead_hunter.main import run
    run()

    # キーワードフィルタに空リストが渡される
    mock_filter_by_keywords.assert_called_once_with([], config.settings)

    # Slack通知は呼ばれない
    mock_notify.assert_not_called()

    # ノイズメールも処理済ラベルを付与（再取得防止）
    mock_mark_as_processed.assert_called_once_with(
        mock_get_gmail_service.return_value,
        ["email-noise-1", "email-noise-2"],
        config.settings,
    )
