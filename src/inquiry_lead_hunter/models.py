from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Email:
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    received_at: str  # ISO 8601
    labels: list[str] = field(default_factory=list)


@dataclass
class ScoredEmail:
    email: Email
    keyword_score: int = 0
    llm_score: Optional[int] = None
    category: Optional[str] = None
    reason: Optional[str] = None
    matched_keywords: list[str] = field(default_factory=list)
