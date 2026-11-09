import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .models import CheckResult, IndexResult, LegalRecord
from .service import LegalRecordDeduplicator


client: InfraiClient | None = None
deduplicator: LegalRecordDeduplicator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global client, deduplicator
    client = InfraiClient()
    deduplicator = LegalRecordDeduplicator(
        client, os.environ.get("LEGAL_RECORD_COLLECTION", "legal-records")
    )
    await deduplicator.prepare()
    yield
    await client.close()


app = FastAPI(title="Legal record duplicate check", lifespan=lifespan)


def service() -> LegalRecordDeduplicator:
    if deduplicator is None:
        raise RuntimeError("Application lifespan has not started")
    return deduplicator


def client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(
        status_code=status,
        detail={"code": error.code, "message": str(error)},
    )


@app.post("/records/index", response_model=IndexResult)
async def index_record(record: LegalRecord) -> IndexResult:
    try:
        return await service().index(record)
    except InfraiError as error:
        raise client_error(error) from error


@app.post("/records/check", response_model=CheckResult)
async def check_record(record: LegalRecord) -> CheckResult:
    try:
        return await service().check(record)
    except InfraiError as error:
        raise client_error(error) from error

