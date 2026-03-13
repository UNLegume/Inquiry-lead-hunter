import logging
import requests

from .models import ScoredEmail

logger = logging.getLogger(__name__)

CATEGORY_LABELS = {
    "meeting_request": "🤝 打ち合わせ・商談依頼",
    "quote_request": "💰 見積もり依頼",
    "interest": "👀 興味・関心",
    "question": "❓ 質問・問い合わせ",
    "partnership": "🤝 パートナー提携・協業",
    "neutral": "📝 中立",
    "rejection": "❌ お断り",
}


def notify(scored_emails: list[ScoredEmail], webhook_url: str) -> None:
    """スコアリング済みメールをSlackに通知"""
    if not scored_emails:
        logger.info("通知対象のメールがありません")
        return

    for scored_email in scored_emails:
        try:
            payload = _build_payload(scored_email)
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Slack通知送信: {scored_email.email.subject}")
        except requests.RequestException as e:
            logger.error(f"Slack通知に失敗: {e}")


def _build_payload(scored_email: ScoredEmail) -> dict:
    """Slack Webhook用のペイロードを構築"""
    email = scored_email.email
    category_label = CATEGORY_LABELS.get(scored_email.category or "", "📝 不明")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎯 商談リード検知 (スコア: {scored_email.llm_score})",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*送信元:*\n{email.sender}"},
                {"type": "mrkdwn", "text": f"*カテゴリ:*\n{category_label}"},
                {"type": "mrkdwn", "text": f"*件名:*\n{email.subject}"},
                {"type": "mrkdwn", "text": f"*キーワードスコア:*\n{scored_email.keyword_score}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*判定理由:*\n{scored_email.reason or '理由なし'}",
            },
        },
    ]

    if scored_email.matched_keywords:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"マッチキーワード: {', '.join(scored_email.matched_keywords)}",
                }
            ],
        })

    blocks.append({"type": "divider"})

    return {"blocks": blocks}


def notify_error(message: str, webhook_url: str) -> None:
    """エラー通知をSlackに送信"""
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ Inquiry Lead Hunter エラー",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{message}```",
                },
            },
        ]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"エラー通知の送信に失敗: {e}")
