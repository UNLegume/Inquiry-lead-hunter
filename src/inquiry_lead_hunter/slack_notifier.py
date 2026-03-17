import logging
import requests

from .models import ScoredEmail

logger = logging.getLogger(__name__)


def notify(scored_emails: list[ScoredEmail], webhook_url: str) -> None:
    """スコアリング済みメールをSlackに1メッセージでまとめて通知"""
    if not scored_emails:
        logger.info("通知対象のメールがありません")
        return

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎯 商談リード検知 ({len(scored_emails)}件)",
            },
        },
    ]

    for scored_email in scored_emails:
        email = scored_email.email
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*送信元:*\n{email.sender}"},
                {"type": "mrkdwn", "text": f"*件名:*\n{email.subject}"},
            ],
        })
        blocks.append({"type": "divider"})

    payload = {"blocks": blocks}
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Slack通知送信: {len(scored_emails)}件のリード")
    except requests.RequestException as e:
        logger.error(f"Slack通知に失敗: {e}")


def notify_no_leads(total_processed: int, webhook_url: str) -> None:
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ リード検知なし",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"処理メール: {total_processed}件 — 該当するリードはありませんでした。",
                },
            },
        ]
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("リード検知なし通知を送信")
    except requests.RequestException as e:
        logger.error(f"リード検知なし通知の送信に失敗: {e}")


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
