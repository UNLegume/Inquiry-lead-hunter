#!/usr/bin/env python3
"""リード回帰テストスクリプト: noise_filter変更後の検証用。

「リード」ラベル付きのGmailメールを全件取得し、_classify_noiseで
各メールが引き続きリードとして認識されるかを検証する。

実行方法:
    PYTHONPATH=src python3 scripts/verify_leads.py
"""
import logging
import sys
from typing import Optional

from inquiry_lead_hunter.config import load_config
from inquiry_lead_hunter.gmail_client import get_gmail_service, _parse_message
from inquiry_lead_hunter.noise_filter import _classify_noise, _extract_sender_domain

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_label_id(service, label_name: str) -> Optional[str]:
    """ラベル名からラベルIDを取得"""
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == label_name:
            return label["id"]
    return None


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
        params = {"userId": "me", "labelIds": [label_id], "maxResults": 500}
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


def is_self_company_sender(sender: str, sender_domains: list[str]) -> bool:
    """送信者が自社ドメインかどうかを確認する。サブドメインにも対応。"""
    sender_domain = _extract_sender_domain(sender)
    if not sender_domain:
        return False
    for domain in sender_domains:
        d = domain.lower()
        if sender_domain == d or sender_domain.endswith("." + d):
            return True
    return False


def get_suggestion(reason: str) -> str:
    """reasonの文字列パターンに基づいて修正提案メッセージを返す"""
    if reason.startswith("self_company_sender"):
        return "→ 修正案: 転送メール(via)の可能性。self_company_sender判定でdisplay name考慮が必要"
    elif reason.startswith("self_company_body"):
        return "→ 修正案: _is_greeting_pattern の宛名認識を拡張、または body_identity_patterns の調整が必要"
    elif reason.startswith("auto_reply"):
        return "→ 修正案: auto_reply_patterns からの該当パターン除外、または条件の絞り込みが必要"
    elif reason.startswith("newsletter"):
        return "→ 修正案: newsletter_patterns からの該当パターン除外が必要"
    elif reason.startswith("bounce"):
        return "→ 修正案: bounce_patterns からの該当パターン除外が必要"
    elif reason.startswith("auto_confirm"):
        return "→ 修正案: auto_confirm_body_patterns の調整、または _strip_quoted_reply の引用検出パターン追加が必要"
    else:
        return "→ 修正案: 該当フィルタールールの見直しが必要"


def classify_emails(emails: list, noise_settings: dict) -> dict:
    """_classify_noiseを各メールに適用し、結果を分類して返す。

    Returns:
        dict with keys:
            "passed": リードとして通過したメール
            "self_excluded": 自社メールとして除外されたメール（正常）
            "warning": 外部送信者だが除外されたメール（要確認）
    """
    auto_reply_patterns: list[str] = noise_settings.get("auto_reply_patterns", [])
    newsletter_patterns: list[str] = noise_settings.get("newsletter_patterns", [])
    bounce_patterns: list[str] = noise_settings.get("bounce_patterns", [])
    auto_confirm_body_patterns: list[str] = noise_settings.get("auto_confirm_body_patterns", [])
    auto_confirm_min_matches: int = noise_settings.get("auto_confirm_min_matches", 2)
    self_company: dict = noise_settings.get("self_company", {})
    sender_domains: list[str] = self_company.get("sender_domains", [])
    body_identity_patterns: list[str] = self_company.get("body_identity_patterns", [])

    results = {"passed": [], "self_excluded": [], "warning": []}

    for email in emails:
        reason = _classify_noise(
            email,
            auto_reply_patterns,
            newsletter_patterns,
            bounce_patterns,
            auto_confirm_body_patterns,
            auto_confirm_min_matches,
            sender_domains,
            body_identity_patterns,
        )

        if reason is None:
            results["passed"].append({"email": email, "reason": None})
        elif is_self_company_sender(email.sender, sender_domains):
            results["self_excluded"].append({"email": email, "reason": reason})
        else:
            results["warning"].append({"email": email, "reason": reason})

    return results


def print_report(results: dict) -> None:
    """分類結果をフォーマットして出力する"""
    passed = results["passed"]
    self_excluded = results["self_excluded"]
    warning = results["warning"]
    total = len(passed) + len(self_excluded) + len(warning)

    print("=" * 64)
    print("リード回帰テスト: noise_filter検証")
    print("=" * 64)
    print()
    print(f"全リードメール: {total}件")
    print(f"├ ✅ リードとして通過: {len(passed)}件")
    print(f"├ 🔵 自社メール（除外は正常）: {len(self_excluded)}件")
    print(f"└ ⚠️  外部送信者だが除外: {len(warning)}件")

    if self_excluded:
        print()
        print("--- 🔵 自社メール（除外は正常） ---")
        for i, item in enumerate(self_excluded, start=1):
            email = item["email"]
            reason = item["reason"]
            print(f"[{i}] sender={email.sender} subject={email.subject}")
            print(f"    reason: {reason}")

    if warning:
        print()
        print("--- ⚠️  要確認: 外部送信者だが除外されたメール ---")
        for i, item in enumerate(warning, start=1):
            email = item["email"]
            reason = item["reason"]
            body_preview = email.body[:200].replace("\n", " ")
            print(f"[{i}] sender={email.sender} subject={email.subject}")
            print(f"    reason: {reason}")
            print(f"    本文冒頭: {body_preview}")
            print(f"    {get_suggestion(reason)}")

    print()
    print("=" * 64)
    if not warning:
        print("結果: PASS（すべてのリードが正しく認識されています）")
    else:
        print(f"結果: FAIL（外部送信者の除外 {len(warning)}件を確認してください）")
    print("=" * 64)


def main():
    logger.info("設定を読み込み中...")
    config = load_config()

    label_lead = config.settings["gmail"]["label_lead"]
    noise_settings = config.settings["noise_filter"]

    logger.info("Gmail APIサービスを構築中...")
    service = get_gmail_service(config.gmail_credentials_path, config.gmail_delegated_user)

    logger.info(f"「{label_lead}」ラベル付きメールを取得中...")
    msg_refs = fetch_all_lead_emails(service, label_lead)

    total = len(msg_refs)
    emails = []
    for i, msg_ref in enumerate(msg_refs, start=1):
        if i % 10 == 0:
            logger.info(f"{i}/{total} 件処理中...")
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()
        email = _parse_message(msg)
        if email is None:
            continue
        emails.append(email)

    results = classify_emails(emails, noise_settings)
    print_report(results)

    if results["warning"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
