import os
from dataclasses import dataclass

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    anthropic_api_key: str
    gmail_credentials_path: str
    gmail_delegated_user: str
    slack_webhook_url: str
    settings: dict
    prompts: dict


def load_config() -> Config:
    load_dotenv()

    settings_path = os.environ.get("SETTINGS_PATH", "config/settings.yaml")
    prompts_path = os.environ.get("PROMPTS_PATH", "config/prompts.yaml")

    with open(settings_path, encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    with open(prompts_path, encoding="utf-8") as f:
        prompts = yaml.safe_load(f)

    return Config(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        gmail_credentials_path=os.environ["GMAIL_CREDENTIALS_PATH"],
        gmail_delegated_user=os.environ["GMAIL_DELEGATED_USER"],
        slack_webhook_url=os.environ["SLACK_WEBHOOK_URL"],
        settings=settings,
        prompts=prompts,
    )
