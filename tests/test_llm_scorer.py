"""Tests for llm_scorer module."""
import json
from unittest.mock import MagicMock, patch

import pytest

from inquiry_lead_hunter.llm_scorer import _parse_response, score_emails, _score_single_email
from inquiry_lead_hunter.models import Email, ScoredEmail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_email(id: str = "msg001") -> Email:
    return Email(
        id=id,
        thread_id="thread001",
        sender="test@example.com",
        subject="テスト件名",
        body="テスト本文",
        received_at="2026-03-13T00:00:00Z",
    )


def _make_scored_email(id: str = "msg001") -> ScoredEmail:
    return ScoredEmail(email=_make_email(id))


def _make_config(threshold: int = 50) -> MagicMock:
    config = MagicMock()
    config.anthropic_api_key = "test-api-key"
    config.prompts = {
        "scoring": {
            "system": "You are a scoring assistant.",
            "user": "sender: {sender}\nsubject: {subject}\nbody: {body}",
        }
    }
    config.settings = {"scoring": {"notification_threshold": threshold}}
    return config


def _make_api_response(score: int, category: str, reason: str) -> MagicMock:
    """Anthropic APIレスポンスのモックを生成"""
    response_text = json.dumps({"score": score, "category": category, "reason": reason})
    content_block = MagicMock()
    content_block.text = response_text
    response = MagicMock()
    response.content = [content_block]
    return response


# ---------------------------------------------------------------------------
# _parse_response tests
# ---------------------------------------------------------------------------

class TestParseResponse:
    def test_valid_json_response(self):
        """正常なJSONレスポンスをパースできる"""
        text = json.dumps({"score": 80, "category": "meeting_request", "reason": "商談依頼です"})
        result = _parse_response(text)

        assert result is not None
        assert result["score"] == 80
        assert result["category"] == "meeting_request"
        assert result["reason"] == "商談依頼です"

    def test_json_wrapped_in_code_block(self):
        """```json```でラップされたレスポンスもパースできる"""
        text = '```json\n{"score": 75, "category": "quote_request", "reason": "見積もり希望"}\n```'
        result = _parse_response(text)

        assert result is not None
        assert result["score"] == 75
        assert result["category"] == "quote_request"
        assert result["reason"] == "見積もり希望"

    def test_json_wrapped_in_plain_code_block(self):
        """``` (言語指定なし) でラップされたレスポンスもパースできる"""
        text = '```\n{"score": 60, "category": "interest", "reason": "興味あり"}\n```'
        result = _parse_response(text)

        assert result is not None
        assert result["score"] == 60
        assert result["category"] == "interest"

    def test_invalid_json_returns_none(self):
        """不正なJSONはNoneを返す"""
        result = _parse_response("これはJSONではありません")
        assert result is None

    def test_score_clamped_above_100(self):
        """スコアが100を超える場合は100にクランプされる"""
        text = json.dumps({"score": 150, "category": "neutral", "reason": "test"})
        result = _parse_response(text)

        assert result is not None
        assert result["score"] == 100

    def test_score_clamped_below_1(self):
        """スコアが1未満の場合は1にクランプされる"""
        text = json.dumps({"score": -10, "category": "neutral", "reason": "test"})
        result = _parse_response(text)

        assert result is not None
        assert result["score"] == 1

    def test_score_zero_clamped_to_1(self):
        """スコアが0の場合は1にクランプされる"""
        text = json.dumps({"score": 0, "category": "neutral", "reason": "test"})
        result = _parse_response(text)

        assert result is not None
        assert result["score"] == 1

    def test_invalid_category_falls_back_to_neutral(self):
        """不正なカテゴリはneutralにフォールバック"""
        text = json.dumps({"score": 50, "category": "unknown_category", "reason": "test"})
        result = _parse_response(text)

        assert result is not None
        assert result["category"] == "neutral"

    def test_all_valid_categories_accepted(self):
        """有効なカテゴリがすべて受け入れられる"""
        valid_categories = [
            "meeting_request", "quote_request", "interest",
            "question", "partnership", "neutral", "rejection"
        ]
        for cat in valid_categories:
            text = json.dumps({"score": 50, "category": cat, "reason": "test"})
            result = _parse_response(text)
            assert result is not None
            assert result["category"] == cat

    def test_empty_string_returns_none(self):
        """空文字列はNoneを返す"""
        result = _parse_response("")
        assert result is None


# ---------------------------------------------------------------------------
# score_emails tests
# ---------------------------------------------------------------------------

class TestScoreEmails:
    def test_email_below_threshold_excluded(self):
        """閾値未満のスコアのメールは結果に含まれない"""
        config = _make_config(threshold=70)
        scored_email = _make_scored_email()

        with patch(
            "inquiry_lead_hunter.llm_scorer._score_single_email"
        ) as mock_score:
            # スコア60 < 閾値70 → 含まれない
            mock_scored = _make_scored_email()
            mock_scored.llm_score = 60
            mock_scored.category = "neutral"
            mock_scored.reason = "低スコア"
            mock_score.return_value = mock_scored

            results = score_emails([scored_email], config)

        assert results == []

    def test_email_at_threshold_included(self):
        """閾値と同じスコアのメールは結果に含まれる"""
        config = _make_config(threshold=70)
        scored_email = _make_scored_email()

        with patch(
            "inquiry_lead_hunter.llm_scorer._score_single_email"
        ) as mock_score:
            mock_scored = _make_scored_email()
            mock_scored.llm_score = 70
            mock_scored.category = "meeting_request"
            mock_scored.reason = "商談依頼"
            mock_score.return_value = mock_scored

            results = score_emails([scored_email], config)

        assert len(results) == 1
        assert results[0].llm_score == 70

    def test_email_above_threshold_included(self):
        """閾値以上のスコアのメールは結果に含まれる"""
        config = _make_config(threshold=50)
        scored_email = _make_scored_email()

        with patch(
            "inquiry_lead_hunter.llm_scorer._score_single_email"
        ) as mock_score:
            mock_scored = _make_scored_email()
            mock_scored.llm_score = 85
            mock_scored.category = "quote_request"
            mock_scored.reason = "見積もり依頼"
            mock_score.return_value = mock_scored

            results = score_emails([scored_email], config)

        assert len(results) == 1
        assert results[0].llm_score == 85

    def test_api_error_skips_email(self):
        """APIエラー時はスキップされる（例外はログのみ、結果に含まれない）"""
        from anthropic import APIError

        config = _make_config(threshold=50)
        scored_email = _make_scored_email()

        with patch(
            "inquiry_lead_hunter.llm_scorer._score_single_email",
            side_effect=Exception("API呼び出し失敗"),
        ):
            results = score_emails([scored_email], config)

        assert results == []

    def test_api_error_does_not_raise(self):
        """APIエラー時に例外が外部に伝播しない"""
        config = _make_config(threshold=50)
        scored_email = _make_scored_email()

        with patch(
            "inquiry_lead_hunter.llm_scorer._score_single_email",
            side_effect=RuntimeError("予期せぬエラー"),
        ):
            # 例外が発生しないことを確認
            results = score_emails([scored_email], config)

        assert results == []

    def test_multiple_emails_filtered_by_threshold(self):
        """複数メールのうち閾値以上のみ返される"""
        config = _make_config(threshold=60)

        emails = [_make_scored_email(f"msg{i:03d}") for i in range(3)]
        scores = [40, 65, 80]

        def mock_score_fn(client, scored_email, prompts):
            idx = int(scored_email.email.id.replace("msg", ""))
            scored_email.llm_score = scores[idx]
            scored_email.category = "neutral"
            scored_email.reason = "test"
            return scored_email

        with patch(
            "inquiry_lead_hunter.llm_scorer._score_single_email",
            side_effect=mock_score_fn,
        ):
            results = score_emails(emails, config)

        assert len(results) == 2
        result_scores = {r.llm_score for r in results}
        assert result_scores == {65, 80}

    def test_empty_input_returns_empty(self):
        """空リストを渡すと空リストが返される"""
        config = _make_config()
        results = score_emails([], config)
        assert results == []
