"""
Gmail API 接続テストスクリプト。

Usage:
    python -m scripts.test_gmail_connection
    python scripts/test_gmail_connection.py
"""

import sys
import os

# プロジェクトルートを sys.path に追加
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# src/ も追加（editable install されていない場合の fallback）
_src_path = os.path.join(_project_root, "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def main():
    from inquiry_lead_hunter.config import load_config
    from inquiry_lead_hunter.gmail_client import get_gmail_service

    print("=== Gmail API 接続テスト ===")
    print()

    # 1. 設定読み込み
    print("[1] 設定を読み込み中...")
    try:
        config = load_config()
        print(f"    credentials_path : {config.gmail_credentials_path}")
        print(f"    delegated_user   : {config.gmail_delegated_user}")
        print("    設定読み込み: OK")
    except Exception as e:
        print(f"    ERROR: 設定読み込みに失敗しました: {e}")
        sys.exit(1)

    print()

    # 2. Gmail API サービス構築
    print("[2] Gmail API サービスを構築中...")
    try:
        service = get_gmail_service(
            config.gmail_credentials_path,
            config.gmail_delegated_user,
        )
        print("    サービス構築: OK")
    except Exception as e:
        print(f"    ERROR: Gmail API サービスの構築に失敗しました: {e}")
        sys.exit(1)

    print()

    # 3. ラベル一覧取得
    print("[3] ラベル一覧を取得中...")
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        if not labels:
            print("    ラベルが見つかりませんでした。")
        else:
            print(f"    取得件数: {len(labels)} 件")
            print()
            print(f"    {'ID':<30} {'名前'}")
            print(f"    {'-'*30} {'-'*30}")
            for label in sorted(labels, key=lambda x: x["name"]):
                print(f"    {label['id']:<30} {label['name']}")
    except Exception as e:
        print(f"    ERROR: ラベル取得に失敗しました: {e}")
        sys.exit(1)

    print()
    print("=== テスト完了 ===")


if __name__ == "__main__":
    main()
