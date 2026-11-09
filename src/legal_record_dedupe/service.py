from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .infrai_client import InfraiClient
from .models import (
    CheckResult,
    DuplicateDecision,
    DuplicateMatch,
    IndexResult,
    LegalRecord,
)


class LegalRecordDeduplicator:
    def __init__(self, gateway: InfraiClient | Any, collection: str) -> None:
        self.gateway = gateway
        self.collection = collection

    async def prepare(self, dimension: int = 1536) -> None:
        await self.gateway.create_collection(self.collection, dimension)

    async def index(self, record: LegalRecord) -> IndexResult:
        text = record.semantic_text()
        embedding = await self.gateway.embedding(text)
        await self.gateway.upsert(
            self.collection,
            record.record_id,
            embedding,
            {
                "kind": record.kind.value,
                "matter_reference": record.matter_reference,
                "summary": text,
            },
        )
        return IndexResult(record_id=record.record_id, indexed=True)

    async def check(self, record: LegalRecord) -> CheckResult:
        text = record.semantic_text()
        embedding = await self.gateway.embedding(text)
        matches = await self.gateway.query(
            self.collection, embedding, record.kind.value
        )
        candidates = [
            match for match in matches if match.get("id") != record.record_id
        ]
        if not candidates:
            return CheckResult(decision=DuplicateDecision.NEW, best_match=None)

        summaries = [item.get("metadata", {}).get("summary", "") for item in candidates]
        ranked = await self.gateway.rerank(text, summaries)
        if not ranked:
            return CheckResult(decision=DuplicateDecision.NEW, best_match=None)

        top = ranked[0]
        candidate = candidates[int(top["index"])]
        score = float(top["score"])
        match = DuplicateMatch(
            record_id=str(candidate["id"]),
            score=score,
            summary=str(candidate.get("metadata", {}).get("summary", "")),
        )
        if score >= 0.88:
            decision = DuplicateDecision.DUPLICATE
        elif score >= 0.72:
            decision = DuplicateDecision.REVIEW
        else:
            decision = DuplicateDecision.NEW
        return CheckResult(decision=decision, best_match=match)
