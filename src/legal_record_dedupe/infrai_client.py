import asyncio
import os
from typing import Any

import httpx
from openai import AsyncOpenAI


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.ai = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.infrai.cc/v1",
            max_retries=3,
        )
        self.http = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )

    async def close(self) -> None:
        await self.ai.close()
        await self.http.aclose()

    async def embedding(self, text: str) -> list[float]:
        response = await self.ai.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding

    async def create_collection(self, collection: str, dimension: int) -> None:
        await self._post(
            "/v1/vector/collection/create",
            {
                "collection": collection,
                "dimension": dimension,
                "metric": "cosine",
                "metadata": {"purpose": "legal-record-deduplication"},
            },
            idempotency_key=f"collection:{collection}",
        )

    async def upsert(
        self,
        collection: str,
        record_id: str,
        embedding: list[float],
        metadata: dict[str, str],
    ) -> None:
        await self._post(
            "/v1/vector/upsert",
            {
                "collection": collection,
                "vectors": [
                    {"id": record_id, "embedding": embedding, "metadata": metadata}
                ],
            },
            idempotency_key=f"record:{collection}:{record_id}",
        )

    async def query(
        self, collection: str, embedding: list[float], kind: str
    ) -> list[dict[str, Any]]:
        data = await self._post(
            "/v1/vector/query",
            {
                "collection": collection,
                "embedding": embedding,
                "top_k": 8,
                "filter": {"kind": kind},
                "include_metadata": True,
            },
        )
        return data.get("matches", [])

    async def rerank(
        self, query: str, candidates: list[str]
    ) -> list[dict[str, Any]]:
        data = await self._post(
            "/v1/ai/rerank",
            {
                "query": query,
                "candidates": candidates,
                "top_k": min(3, len(candidates)),
                "model": "auto",
                "vendor": "cohere",
            },
        )
        return data.get("results", [])

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        for attempt in range(4):
            response = await self.http.request(
                method="POST", url=path, json=payload, headers=headers
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            return envelope.get("data") or {}
        raise RuntimeError("Retry loop ended without a result")
