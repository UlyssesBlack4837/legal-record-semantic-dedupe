from enum import Enum

from pydantic import BaseModel, Field


class RecordKind(str, Enum):
    MATTER_INTAKE = "matter_intake"
    SIGNED_DOCUMENT_DELIVERY = "signed_document_delivery"
    DEADLINE_FOLLOW_UP = "deadline_follow_up"


class LegalRecord(BaseModel):
    record_id: str = Field(min_length=1)
    kind: RecordKind
    matter_reference: str = Field(min_length=1)
    party_name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    event_date: str = Field(min_length=1, description="ISO 8601 date or timestamp")

    def semantic_text(self) -> str:
        return " | ".join(
            (
                f"kind: {self.kind.value}",
                f"matter: {self.matter_reference}",
                f"party: {self.party_name}",
                f"date: {self.event_date}",
                f"details: {self.summary}",
            )
        )


class DuplicateMatch(BaseModel):
    record_id: str
    score: float
    summary: str


class DuplicateDecision(str, Enum):
    DUPLICATE = "duplicate"
    REVIEW = "review"
    NEW = "new"


class CheckResult(BaseModel):
    decision: DuplicateDecision
    best_match: DuplicateMatch | None


class IndexResult(BaseModel):
    record_id: str
    indexed: bool

