import asyncio

from legal_record_dedupe.models import DuplicateDecision, LegalRecord, RecordKind
from legal_record_dedupe.service import LegalRecordDeduplicator


class StubGateway:
    async def embedding(self, text: str) -> list[float]:
        return [0.1, 0.2]

    async def create_collection(self, collection: str, dimension: int) -> None:
        return None

    async def upsert(self, collection, record_id, embedding, metadata) -> None:
        return None

    async def query(self, collection, embedding, kind) -> list[dict]:
        return [
            {
                "id": "intake-2026-0042",
                "metadata": {
                    "summary": "kind: matter_intake | matter: HARBOR-42 | party: North Harbor Imports | date: 2026-09-03 | details: Supplier contract dispute for delayed ceramic stock"
                },
            }
        ]

    async def rerank(self, query, candidates) -> list[dict]:
        return [{"index": 0, "score": 0.93}]


def test_repeated_intake_is_held_as_duplicate() -> None:
    record = LegalRecord(
        record_id="intake-2026-0042-copy",
        kind=RecordKind.MATTER_INTAKE,
        matter_reference="HARBOR-42",
        party_name="North Harbor Imports",
        summary="Delayed ceramic inventory caused a supplier contract dispute.",
        event_date="2026-09-04",
    )

    result = asyncio.run(
        LegalRecordDeduplicator(StubGateway(), "legal-records").check(record)
    )

    assert result.decision is DuplicateDecision.DUPLICATE
    assert result.best_match is not None
    assert result.best_match.record_id == "intake-2026-0042"
    assert result.best_match.score == 0.93
