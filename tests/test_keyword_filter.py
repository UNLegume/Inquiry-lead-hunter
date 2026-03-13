"""Tests for keyword_filter.filter_by_keywords."""

import pytest

from inquiry_lead_hunter.models import Email, ScoredEmail
from inquiry_lead_hunter.keyword_filter import filter_by_keywords


class TestFilterByKeywords:
    """Unit tests for filter_by_keywords()."""

    # ------------------------------------------------------------------
    # 1. High keyword → score >= 30
    # ------------------------------------------------------------------

    def test_high_keyword_score_at_least_30(self, high_keyword_email, settings):
        """An email with one high keyword must have keyword_score >= 30."""
        # "デモ" is in high_keywords (weight 30); threshold is 50 so only
        # check the score value directly by lowering the threshold.
        low_threshold_settings = {
            **settings,
            "scoring": {"llm_threshold": 0},
        }
        results = filter_by_keywords([high_keyword_email], low_threshold_settings)
        assert len(results) == 1
        assert results[0].keyword_score >= 30

    # ------------------------------------------------------------------
    # 2. High + medium keywords → score >= 45
    # ------------------------------------------------------------------

    def test_high_and_medium_keywords_score_at_least_45(
        self, high_and_medium_email, settings
    ):
        """An email with one high and one medium keyword must score >= 45."""
        low_threshold_settings = {
            **settings,
            "scoring": {"llm_threshold": 0},
        }
        results = filter_by_keywords([high_and_medium_email], low_threshold_settings)
        assert len(results) == 1
        assert results[0].keyword_score >= 45

    # ------------------------------------------------------------------
    # 3. Two high keywords → score 60 (above threshold 50)
    # ------------------------------------------------------------------

    def test_two_high_keywords_score_60_passes_threshold(
        self, two_high_keywords_email, settings
    ):
        """Two distinct high keywords must yield score=60 and be returned."""
        results = filter_by_keywords([two_high_keywords_email], settings)
        assert len(results) == 1
        scored = results[0]
        assert scored.keyword_score == 60

    # ------------------------------------------------------------------
    # 4. Medium keyword only → score 15, below threshold → not returned
    # ------------------------------------------------------------------

    def test_medium_only_below_threshold_not_returned(
        self, medium_only_email, settings
    ):
        """An email with only one medium keyword (score=15) must not pass threshold."""
        results = filter_by_keywords([medium_only_email], settings)
        assert results == []

    # ------------------------------------------------------------------
    # 5. Negative keyword → score reset to 0 → not returned
    # ------------------------------------------------------------------

    def test_negative_keyword_zeroes_score(self, negative_keyword_email, settings):
        """A negative keyword must reset the score to 0 and exclude the email."""
        results = filter_by_keywords([negative_keyword_email], settings)
        assert results == []

    def test_negative_keyword_zeroes_score_value(
        self, negative_keyword_email, settings
    ):
        """After a negative keyword match, keyword_score must equal 0."""
        low_threshold_settings = {
            **settings,
            "scoring": {"llm_threshold": 0},
        }
        results = filter_by_keywords([negative_keyword_email], low_threshold_settings)
        assert len(results) == 1
        assert results[0].keyword_score == 0

    # ------------------------------------------------------------------
    # 6. matched_keywords recorded correctly
    # ------------------------------------------------------------------

    def test_matched_keywords_recorded_for_two_high_keywords(
        self, two_high_keywords_email, settings
    ):
        """matched_keywords must contain every keyword that contributed to the score."""
        results = filter_by_keywords([two_high_keywords_email], settings)
        assert len(results) == 1
        matched = results[0].matched_keywords
        # Both "見積もり" and "デモ" appear in the email body
        assert "見積もり" in matched
        assert "デモ" in matched

    def test_matched_keywords_no_duplicates(self, settings):
        """A keyword appearing multiple times in the text must be counted only once."""
        email = Email(
            id="dup-001",
            thread_id="t-dup-001",
            sender="buyer@example.com",
            subject="見積もり",
            body="見積もりをお願いします。見積もりの件、よろしくお願いします。",
            received_at="2026-03-13T12:00:00Z",
        )
        low_threshold_settings = {
            **settings,
            "scoring": {"llm_threshold": 0},
        }
        results = filter_by_keywords([email], low_threshold_settings)
        assert len(results) == 1
        assert results[0].matched_keywords.count("見積もり") == 1
        # Score must be exactly 30 (one occurrence counted once)
        assert results[0].keyword_score == 30

    def test_matched_keywords_for_high_and_medium(
        self, high_and_medium_email, settings
    ):
        """matched_keywords must include both the high and medium matched keywords."""
        low_threshold_settings = {
            **settings,
            "scoring": {"llm_threshold": 0},
        }
        results = filter_by_keywords([high_and_medium_email], low_threshold_settings)
        assert len(results) == 1
        matched = results[0].matched_keywords
        # "pricing" is a high keyword; "興味があります" is a medium keyword
        assert "pricing" in matched
        assert "興味があります" in matched

    # ------------------------------------------------------------------
    # 7. Empty list input
    # ------------------------------------------------------------------

    def test_empty_list_returns_empty(self, settings):
        """Passing an empty list must return an empty list without error."""
        results = filter_by_keywords([], settings)
        assert results == []

    # ------------------------------------------------------------------
    # 8. Return type is ScoredEmail
    # ------------------------------------------------------------------

    def test_returns_scored_email_instances(self, two_high_keywords_email, settings):
        """Each returned element must be a ScoredEmail instance."""
        results = filter_by_keywords([two_high_keywords_email], settings)
        assert len(results) == 1
        assert isinstance(results[0], ScoredEmail)

    # ------------------------------------------------------------------
    # 9. No keyword match → score 0 → not returned
    # ------------------------------------------------------------------

    def test_no_keyword_match_not_returned(self, settings):
        """An email with no matching keywords must not be returned."""
        email = Email(
            id="no-kw-001",
            thread_id="t-no-kw-001",
            sender="random@example.com",
            subject="Hello",
            body="Just saying hi!",
            received_at="2026-03-13T09:00:00Z",
        )
        results = filter_by_keywords([email], settings)
        assert results == []

    # ------------------------------------------------------------------
    # 10. Email object is preserved inside ScoredEmail
    # ------------------------------------------------------------------

    def test_original_email_preserved_in_scored_email(
        self, two_high_keywords_email, settings
    ):
        """The ScoredEmail.email attribute must be the original Email object."""
        results = filter_by_keywords([two_high_keywords_email], settings)
        assert len(results) == 1
        assert results[0].email is two_high_keywords_email
