import logging
import base64
from googleapiclient.discovery import build
from google.oauth2 import service_account

from .models import Email

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_gmail_service(credentials_path: str, delegated_user: str):
    """Gmail APIサービスを構築して返す。サービスアカウント + ドメイン全体の委任。"""
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    delegated_credentials = credentials.with_subject(delegated_user)
    return build("gmail", "v1", credentials=delegated_credentials)


def _get_label_id(service, label_name: str) -> str | None:
    """ラベル名からラベルIDを取得"""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]
    return None


def fetch_inquiry_emails(service, settings: dict) -> list[Email]:
    """「問い合わせ」ラベル付き & 「処理済」ラベルなしのメールを取得"""
    label_inquiry = settings["gmail"]["label_inquiry"]
    label_processed = settings["gmail"]["label_processed"]
    max_results = settings["gmail"]["max_results"]

    inquiry_label_id = _get_label_id(service, label_inquiry)
    if not inquiry_label_id:
        logger.warning(f"ラベル '{label_inquiry}' が見つかりません")
        return []

    processed_label_id = _get_label_id(service, label_processed)

    # 問い合わせラベル付きメールを取得
    query_params = {
        "userId": "me",
        "labelIds": [inquiry_label_id],
        "maxResults": max_results,
    }

    results = service.users().messages().list(**query_params).execute()
    messages = results.get("messages", [])

    emails = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()

        # 処理済ラベルがついていたらスキップ
        msg_labels = msg.get("labelIds", [])
        if processed_label_id and processed_label_id in msg_labels:
            continue

        email = _parse_message(msg)
        if email:
            emails.append(email)

    logger.info(f"{len(emails)}件の未処理メールを取得")
    return emails


def _parse_message(msg: dict) -> Email | None:
    """Gmail APIのメッセージをEmailデータクラスに変換"""
    try:
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

        sender = headers.get("from", "")
        subject = headers.get("subject", "")
        date = headers.get("date", "")

        body = _extract_body(msg["payload"])

        return Email(
            id=msg["id"],
            thread_id=msg["threadId"],
            sender=sender,
            subject=subject,
            body=body,
            received_at=date,
            labels=msg.get("labelIds", []),
        )
    except Exception as e:
        logger.error(f"メッセージのパースに失敗: {e}")
        return None


def _extract_body(payload: dict) -> str:
    """メール本文をプレーンテキストで抽出"""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        # 再帰的にネストされたpartsを探索
        if part.get("parts"):
            result = _extract_body(part)
            if result:
                return result

    return ""


def mark_as_lead(service, email_ids: list[str], settings: dict) -> None:
    """メールに「リード」ラベルを付与"""
    label_lead = settings["gmail"]["label_lead"]

    lead_label_id = _get_label_id(service, label_lead)
    if not lead_label_id:
        # ラベルが存在しない場合は作成
        label_body = {
            "name": label_lead,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created = service.users().labels().create(userId="me", body=label_body).execute()
        lead_label_id = created["id"]
        logger.info(f"ラベル '{label_lead}' を作成しました")

    for email_id in email_ids:
        try:
            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": [lead_label_id]},
            ).execute()
            logger.debug(f"メール {email_id} にリードラベルを付与")
        except Exception as e:
            logger.error(f"ラベル付与に失敗 (メール: {email_id}): {e}")


def mark_as_processed(service, email_ids: list[str], settings: dict) -> None:
    """メールに「処理済」ラベルを付与"""
    label_processed = settings["gmail"]["label_processed"]

    processed_label_id = _get_label_id(service, label_processed)
    if not processed_label_id:
        # ラベルが存在しない場合は作成
        label_body = {
            "name": label_processed,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created = service.users().labels().create(userId="me", body=label_body).execute()
        processed_label_id = created["id"]
        logger.info(f"ラベル '{label_processed}' を作成しました")

    for email_id in email_ids:
        try:
            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": [processed_label_id]},
            ).execute()
            logger.debug(f"メール {email_id} に処理済ラベルを付与")
        except Exception as e:
            logger.error(f"ラベル付与に失敗 (メール: {email_id}): {e}")
