"""
Slack 通知テストスクリプト。
テスト用の ScoredEmail を作成して Slack webhook に通知を送信し、動作を確認する。

Usage:
    python -m scripts.test_slack_notification
    python scripts/test_slack_notification.py
"""

import sys
import os

# プロジェクトルートを sys.path に追加
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

_src_path = os.path.join(_project_root, "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def main():
    from inquiry_lead_hunter.config import load_config
    from inquiry_lead_hunter.models import Email, ScoredEmail
    from inquiry_lead_hunter.slack_notifier import notify, notify_error

    print("=== Slack 通知テスト ===")
    print()

    # 1. 設定読み込み
    print("[1] 設定を読み込み中...")
    try:
        config = load_config()
        print(f"    webhook_url: {config.slack_webhook_url[:40]}...")
        print("    設定読み込み: OK")
    except Exception as e:
        print(f"    ERROR: 設定読み込みに失敗しました: {e}")
        sys.exit(1)

    print()

    # 2. テスト用 ScoredEmail を作成
    print("[2] テスト用 ScoredEmail を作成中...")

    test_emails = [
        ScoredEmail(
            email=Email(
                id="test-slack-001",
                thread_id="thread-slack-001",
                sender="prospect@bigcorp.com",
                subject="御社サービスの導入を検討しています",
                body=(
                    "はじめまして。株式会社ビッグコープの田中と申します。\n"
                    "見積もりとデモのご提供をお願いできますでしょうか。"
                ),
                received_at="2026-03-13T09:00:00Z",
                labels=["INBOX"],
            ),
            keyword_score=60,
            llm_score=85,
            category="高確度リード",
            reason="見積もりとデモの依頼が含まれており、導入意向が明確。",
            matched_keywords=["見積もり", "デモ"],
        ),
        ScoredEmail(
            email=Email(
                id="test-slack-002",
                thread_id="thread-slack-002",
                sender="info@startup.io",
                subject="資料請求について",
                body="御社のプロダクトに興味があります。詳細な資料をお送りください。",
                received_at="2026-03-13T10:00:00Z",
                labels=["INBOX"],
            ),
            keyword_score=30,
            llm_score=62,
            category="中確度リード",
            reason="資料請求の依頼あり。具体的な導入検討段階かは不明。",
            matched_keywords=["資料請求"],
        ),
    ]

    print(f"    作成件数: {len(test_emails)} 件")
    print()

    # 3. 通常通知
    print("[3] リード通知を送信中...")
    try:
        notify(test_emails, config.slack_webhook_url)
        print("    通知送信: OK")
    except Exception as e:
        print(f"    ERROR: 通知送信に失敗しました: {e}")
        sys.exit(1)

    print()

    # 4. エラー通知
    print("[4] エラー通知を送信中...")
    try:
        notify_error(
            "テスト用エラーメッセージ: これは test_slack_notification.py からの動作確認です。",
            config.slack_webhook_url,
        )
        print("    エラー通知送信: OK")
    except Exception as e:
        print(f"    ERROR: エラー通知送信に失敗しました: {e}")
        sys.exit(1)

    print()
    print("=== テスト完了 ===")
    print()
    print("Slack チャンネルに以下が届いていることを確認してください:")
    print("  - リード通知メッセージ (2件)")
    print("  - エラー通知メッセージ (1件)")


if __name__ == "__main__":
    main()
