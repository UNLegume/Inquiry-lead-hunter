import json
import logging
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from anthropic import APIError, RateLimitError

from .models import ScoredEmail

logger = logging.getLogger(__name__)

MAX_BODY_LENGTH = 3000


def score_emails(scored_emails: list[ScoredEmail], config) -> list[ScoredEmail]:
    """Claude APIでメールをスコアリング。閾値以上のスコアのメールのみ返却。"""
    client = Anthropic(api_key=config.anthropic_api_key)
    prompts = config.prompts["scoring"]
    threshold = config.settings["scoring"]["notification_threshold"]

    results = []
    for scored_email in scored_emails:
        try:
            result = _score_single_email(client, scored_email, prompts)
            if result and result.llm_score is not None and result.llm_score >= threshold:
                results.append(result)
        except Exception as e:
            logger.error(f"スコアリング失敗 (メール: {scored_email.email.id}): {e}")
            # エラーのメールはresultsに含めない（次回再処理のため）
            # scored_emailを返さないことで、mark_as_processedの対象外になる

    return results


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((APIError, RateLimitError)),
    reraise=True,
)
def _score_single_email(client: Anthropic, scored_email: ScoredEmail, prompts: dict) -> ScoredEmail:
    """1件のメールをClaude APIでスコアリング"""
    email = scored_email.email
    body = email.body[:MAX_BODY_LENGTH]

    user_message = prompts["user"].format(
        sender=email.sender,
        subject=email.subject,
        body=body,
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        temperature=0.1,
        system=prompts["system"],
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = response.content[0].text
    parsed = _parse_response(response_text)

    if parsed:
        scored_email.llm_score = parsed["score"]
        scored_email.category = parsed["category"]
        scored_email.reason = parsed["reason"]

    return scored_email


def _parse_response(response_text: str) -> dict | None:
    """Claude APIのレスポンスからJSONをパース"""
    try:
        # JSONブロックを抽出（```json ... ``` でラップされている場合も対応）
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        data = json.loads(text)

        # バリデーション
        score = int(data.get("score", 0))
        score = max(1, min(100, score))

        valid_categories = {
            "meeting_request", "quote_request", "interest",
            "question", "neutral", "rejection"
        }
        category = data.get("category", "neutral")
        if category not in valid_categories:
            category = "neutral"

        return {
            "score": score,
            "reason": str(data.get("reason", "")),
            "category": category,
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"レスポンスのパースに失敗: {e}\n{response_text}")
        return None
