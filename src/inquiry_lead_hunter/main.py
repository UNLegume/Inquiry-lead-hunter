import logging
import sys

from .config import load_config
from .gmail_client import get_gmail_service, fetch_inquiry_emails, mark_as_processed, mark_as_lead
from .noise_filter import filter_noise
from .keyword_filter import filter_by_keywords
from .llm_scorer import score_emails
from .slack_notifier import notify, notify_error

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def run():
    """メインの処理フロー"""
    setup_logging()
    logger.info("Inquiry Lead Hunter 開始")

    try:
        # 1. 設定読み込み
        config = load_config()

        # 2. Gmail APIサービス構築
        service = get_gmail_service(
            config.gmail_credentials_path,
            config.gmail_delegated_user,
        )

        # 3〜8. 未処理メールがなくなるまでバッチ処理を繰り返す
        batch_num = 0
        total_processed = 0
        total_leads = 0

        while True:
            batch_num += 1
            emails = fetch_inquiry_emails(service, config.settings)
            if not emails:
                logger.info("未処理メールなし。ループ終了。")
                break
            logger.info(f"バッチ{batch_num}: {len(emails)}件のメールを取得")

            # 4. ノイズ除外
            clean_emails = filter_noise(emails, config.settings["noise_filter"])
            noise_count = len(emails) - len(clean_emails)
            logger.info(f"ノイズ除外: {noise_count}件除外, {len(clean_emails)}件残存")

            # 5. キーワードフィルタ
            candidates = filter_by_keywords(clean_emails, config.settings)
            logger.info(f"キーワードフィルタ: {len(candidates)}件が候補")

            # 6. LLMスコアリング
            scored = score_emails(candidates, config)
            logger.info(f"LLMスコアリング: {len(scored)}件が閾値超え")

            # 7. 処理済ラベル付与
            llm_error_ids = set()
            for c in candidates:
                if c.llm_score is None:
                    llm_error_ids.add(c.email.id)

            all_email_ids = [e.id for e in emails]
            ids_to_mark = [eid for eid in all_email_ids if eid not in llm_error_ids]

            if ids_to_mark:
                mark_as_processed(service, ids_to_mark, config.settings)
                logger.info(f"{len(ids_to_mark)}件を処理済みに設定")

            # 8. Slack通知
            if scored:
                lead_ids = [c.email.id for c in scored]
                mark_as_lead(service, lead_ids, config.settings)
                logger.info(f"{len(scored)}件にリードラベルを付与")
                notify(scored, config.slack_webhook_url)
                logger.info(f"{len(scored)}件のリードをSlack通知")

            total_processed += len(ids_to_mark)
            total_leads += len(scored)

            # LLMエラーだけ残った場合は無限ループ防止
            if len(ids_to_mark) == 0:
                logger.warning("処理済みにできるメールがありません。ループ終了。")
                break

        logger.info(f"Inquiry Lead Hunter 完了 — 合計処理: {total_processed}件, リード検知: {total_leads}件")

    except Exception as e:
        logger.exception(f"致命的エラー: {e}")
        try:
            config = load_config()
            notify_error(str(e), config.slack_webhook_url)
        except Exception:
            pass
        sys.exit(1)


def main():
    """エントリポイント"""
    run()


if __name__ == "__main__":
    main()
