"""
Claude API スコアリングテストスクリプト。
ハードコードされたサンプルメールを使い、LLM スコアリングの動作を確認する。

Usage:
    python -m scripts.test_claude_scoring
    python scripts/test_claude_scoring.py
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


# ---------------------------------------------------------------------------
# サンプルメールデータ
# ---------------------------------------------------------------------------

SAMPLE_EMAILS = [
    {
        "id": "sample-001",
        "sender": "prospect@bigcorp.com",
        "subject": "御社サービスの導入を検討しています",
        "body": (
            "はじめまして。株式会社ビッグコープの田中と申します。\n"
            "御社のサービスについて詳しく伺いたく、ご連絡いたしました。\n"
            "現在、社内の業務効率化を目的としてツール導入を検討しており、\n"
            "見積もりとデモのご提供をお願いできますでしょうか。\n"
            "ご多忙のところ恐縮ですが、よろしくお願いいたします。"
        ),
    },
    {
        "id": "sample-002",
        "sender": "info@startup.io",
        "subject": "資料請求について",
        "body": (
            "お世話になります。\n"
            "御社のプロダクトに興味があります。\n"
            "詳細な資料をお送りいただけますでしょうか。"
        ),
    },
    {
        "id": "sample-003",
        "sender": "jobseeker@example.com",
        "subject": "採用について",
        "body": (
            "貴社の採用情報を拝見しました。\n"
            "エンジニアポジションへの応募を検討しております。\n"
            "詳細をお教えいただけますでしょうか。"
        ),
    },
    {
        "id": "sample-004",
        "sender": "noreply@news.example.com",
        "subject": "今月のニュースレター",
        "body": (
            "今月の特集記事をお届けします。\n"
            "配信停止はこちら: https://example.com/unsubscribe"
        ),
    },
]


def main():
    from inquiry_lead_hunter.config import load_config
    from inquiry_lead_hunter.models import Email, ScoredEmail
    from inquiry_lead_hunter.llm_scorer import score_emails

    print("=== Claude API スコアリングテスト ===")
    print()

    # 1. 設定読み込み
    print("[1] 設定を読み込み中...")
    try:
        config = load_config()
        print("    設定読み込み: OK")
    except Exception as e:
        print(f"    ERROR: 設定読み込みに失敗しました: {e}")
        sys.exit(1)

    print()

    # 2. サンプルメールを Email オブジェクトに変換し ScoredEmail を作成
    print(f"[2] サンプルメール {len(SAMPLE_EMAILS)} 件を準備")
    scored_inputs = []
    for sample in SAMPLE_EMAILS:
        email = Email(
            id=sample["id"],
            thread_id=f"thread-{sample['id']}",
            sender=sample["sender"],
            subject=sample["subject"],
            body=sample["body"],
            received_at="2026-03-13T09:00:00Z",
            labels=["INBOX"],
        )
        scored_inputs.append(
            ScoredEmail(
                email=email,
                keyword_score=30,  # スコアリングテスト用のダミー値
                matched_keywords=["テスト"],
            )
        )

    print()

    # 3. LLM スコアリング実行
    print("[3] Claude API でスコアリング中...")
    try:
        results = score_emails(scored_inputs, config)
    except Exception as e:
        print(f"    ERROR: スコアリングに失敗しました: {e}")
        sys.exit(1)

    print(f"    完了: {len(results)} 件が閾値を超えました")
    print()

    # 4. 結果表示
    print("[4] スコアリング結果")
    print()

    result_map = {r.email.id: r for r in results}

    for sample in SAMPLE_EMAILS:
        sid = sample["id"]
        print(f"  [{sid}] {sample['subject'][:40]}")
        print(f"    送信者    : {sample['sender']}")

        if sid in result_map:
            r = result_map[sid]
            print(f"    LLMスコア : {r.llm_score}")
            print(f"    カテゴリ  : {r.category}")
            print(f"    理由      : {r.reason}")
        else:
            # results に含まれない = 閾値未満 or エラー
            # scored_inputs から対応オブジェクトを探して llm_score を確認
            matched = next((s for s in scored_inputs if s.email.id == sid), None)
            if matched and matched.llm_score is not None:
                print(f"    LLMスコア : {matched.llm_score} (閾値未満)")
                print(f"    カテゴリ  : {matched.category}")
                print(f"    理由      : {matched.reason}")
            else:
                print("    → 閾値未満またはスコアリングエラー")
        print()

    print("=== テスト完了 ===")


if __name__ == "__main__":
    main()
