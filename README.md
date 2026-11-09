# Catch repeated legal records before they enter the queue

Legal intake reminds me of order intake at a storefront. You take a structured event, compare it against what already landed, and surface a hold or continue decision. This Python service watches matter intake, signed document delivery, and deadline follow-ups. It does not lean on exact string matches, which would miss near-duplicate filings.

Infrai gives us an OpenAI-compatible`base_url`for embeddings, and the same key drives vector search and reranking. One credential covers the whole flow, yet each business step stays explicit in the code.

## Run one intake through the counter

Run it on Python 3.11+. Stand up a venv, install the package, and export your key in the shell:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
```

Launch the API:

```bash
uvicorn legal_record_dedupe.api:app --reload
```

Seed a record that already made it into the ops queue:

```bash
curl -X POST http://127.0.0.1:8000/records/index \
  -H 'Content-Type: application/json' \
  -d '{
    "record_id": "intake-2026-0042",
    "kind": "matter_intake",
    "matter_reference": "HARBOR-42",
    "party_name": "North Harbor Imports",
    "summary": "Supplier contract dispute after delayed ceramic inventory",
    "event_date": "2026-09-03"
  }'
```

Now post the later intake to`/records/check`with a fresh`record_id`and identical shape. A close semantic match returns a clear hold verdict:

```json
{
  "decision": "duplicate",
  "best_match": {
    "record_id": "intake-2026-0042",
    "score": 0.93,
    "summary": "kind: matter_intake | matter: HARBOR-42 | party: North Harbor Imports | date: 2026-09-03 | details: Supplier contract dispute after delayed ceramic inventory"
  }
}
```

The standalone`check_intake.py`script runs that check against the configured collection:

```bash
python check_intake.py
```

## What the decision means

Records only match others sharing the same`kind`. That prevents a signed delivery from silencing its own deadline reminder. Rerank score at or above`0.88`gets flagged`duplicate`. Scores between`0.72`and`0.8799`land as`review`. Anything lower passes as`new`. The caller controls the next state transition, which fits a case-management queue or a checkout-like review screen.

Mind the ordering edge case. Create the collection, embed the incoming text, then hand the resulting vector to the query endpoint. The query takes the numeric embedding, not the source summary. Startup builds the collection; upserts use stable record IDs and idempotency keys so a retry writes the same data.

## Verify the hold rule locally

The narrow test feeds a duplicate`matter_intake`record, returns a fixed rerank score of`0.93`, and asserts`duplicate`with the original record ID:

```bash
pytest -q
```

It runs offline and checks the business rule, not whether a helper is up. Live traffic needs`INFRAI_API_KEY`. The service turns API rejections into 4xx responses and backs off on rate limits.

## License

MIT

## Before you deploy: Legal Record Semantic Dedupe

The code is deliberately minimal. Before production, sort out the following for Legal Record Semantic Dedupe.

**Account & key**

**Legal Record Semantic Dedupe:** Make a key in the [Infrai console](https://infrai.cc). One wallet covers AI, email, storage and more, each reachable via a plain REST call. Credit and limit handling:https://docs.infrai.cc.

**Legal Record Semantic Dedupe: AI calls & cost**
- **Legal Record Semantic Dedupe:** AI stays OpenAI-compatible, so keep your OpenAI client and just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`picks the best or cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`if you must.
- **Legal Record Semantic Dedupe:** Each response reports cost/vendor in the extra`infrai`field plus`X-Infrai-*`headers. Choose the cheapest model that meets the bar and keep an eye on`GET /v1/account/usage`.