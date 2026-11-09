import asyncio
import os

from legal_record_dedupe.infrai_client import InfraiClient
from legal_record_dedupe.models import LegalRecord, RecordKind
from legal_record_dedupe.service import LegalRecordDeduplicator


async def main() -> None:
    client = InfraiClient()
    checker = LegalRecordDeduplicator(
        client, os.environ.get("LEGAL_RECORD_COLLECTION", "legal-records")
    )
    try:
        await checker.prepare()
        record = LegalRecord(
            record_id="intake-2026-0042-received-again",
            kind=RecordKind.MATTER_INTAKE,
            matter_reference="HARBOR-42",
            party_name="North Harbor Imports",
            summary="New intake for a supplier contract dispute over delayed ceramic stock.",
            event_date="2026-09-04",
        )
        result = await checker.check(record)
        print(result.model_dump_json(indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

