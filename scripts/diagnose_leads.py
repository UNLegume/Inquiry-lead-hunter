"""
診断スクリプト: 「リード」ラベル付きメールの件名・送信元・本文冒頭を取得して表示する。

実行方法:
    PYTHONPATH=src python3 scripts/diagnose_leads.py
"""
import base64
import logging
import sys
from typing import Optional

from inquiry_lead_hunter.config import load_config
from inquiry_lead_hunter.gmail_client import get_gmail_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_label_id(service, label_name: str) -> Optional[str]:
    """ラベル名からラベルIDを取得"""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]
    return None


def extract_body(payload: dict) -> str:
    """メール本文をプレーンテキストで抽出"""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        if part.get("parts"):
            result = extract_body(part)
            if result:
                return result

    return ""


def fetch_all_lead_emails(service, label_name: str) -> list:
    """「リード」ラベル付きメールを全件取得（ページネーション対応）"""
    label_id = get_label_id(service, label_name)
    if not label_id:
        logger.error(f"ラベル '{label_name}' が見つかりません")
        return []

    logger.info(f"ラベル '{label_name}' のID: {label_id}")

    messages = []
    page_token = None

    while True:
        params = {
            "userId": "me",
            "labelIds": [label_id],
            "maxResults": 500,
        }
        if page_token:
            params["pageToken"] = page_token

        results = service.users().messages().list(**params).execute()
        page_messages = results.get("messages", [])
        messages.extend(page_messages)

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    logger.info(f"合計 {len(messages)} 件のメッセージIDを取得")
    return messages


def main():
    logger.info("設定を読み込み中...")
    config = load_config()

    label_lead = config.settings["gmail"]["label_lead"]
    logger.info(f"対象ラベル: '{label_lead}'")

    logger.info("Gmail APIサービスを構築中...")
    service = get_gmail_service(config.gmail_credentials_path, config.gmail_delegated_user)

    logger.info(f"「{label_lead}」ラベル付きメールを取得中...")
    msg_refs = fetch_all_lead_emails(service, label_lead)

    if not msg_refs:
        print(f"\n「{label_lead}」ラベル付きメールは0件でした。")
        sys.exit(0)

    print(f"\n{'='*70}")
    print(f"「{label_lead}」ラベル付きメール: {len(msg_refs)} 件")
    print(f"{'='*70}\n")

    for i, msg_ref in enumerate(msg_refs, start=1):
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        sender = headers.get("from", "(不明)")
        subject = headers.get("subject", "(件名なし)")
        date = headers.get("date", "(日付不明)")
        body = extract_body(msg["payload"])
        body_preview = body[:200].replace("\n", " ").strip()

        print(f"[{i}/{len(msg_refs)}] ID: {msg_ref['id']}")
        print(f"  日付    : {date}")
        print(f"  送信元  : {sender}")
        print(f"  件名    : {subject}")
        print(f"  本文冒頭: {body_preview}")
        print()

    print(f"{'='*70}")
    print(f"完了: {len(msg_refs)} 件を表示しました。")


if __name__ == "__main__":
    main()
