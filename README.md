# Employee Support Desk

Local assessment implementation with a Spring Boot public API and a Python FastAPI service. It answers policy questions and produces human-review reports from batches of synthetic reimbursement documents. It never approves claims, initiates payments, or sends messages.

## Architecture

```text
Caller -> Spring Boot :8080
          /answer  -> trusted identity + validation -> Python /internal/answer
          /batches -> manifest validation -> each file -> Python /internal/document
                                                       |
                         TXT/PDF extraction + evidence-backed fields
                                                       |
                         eligible policies -> offline provider -> validated answer
```

Java owns caller context, the public response, multipart validation, duplicate detection, item failure isolation, and batch ordering. Python owns extraction, evidence selection, policy outcomes, and generation. Internal requests contain server-derived tenant/role. Python endpoints have no separate authentication: bind them to loopback for this exercise and expose only Java to callers.

The offline provider is a deterministic model double. No API key, paid model, database, frontend, or OCR is required. Only eligible policy quotations reach it; document instructions cannot override identity or application behavior.

## Prerequisites and startup (Windows PowerShell)

Use Python 3.11+ and JDK 21. The Maven wrapper is included. Dependency installation needs internet; once installed, the application and tests run without a model/network service.

In terminal 1, from the repository root:

```powershell
cd python-service
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In terminal 2, from the repository root:

```powershell
cd spring-api
.\mvnw.cmd spring-boot:run
```

Restart Java after Java code changes. If Python has no `uvicorn` module, install requirements using the exact virtual-environment executable above. Python documentation is at http://localhost:8000/docs.

Configuration:

| Setting | Default |
|---|---|
| Java port | 8080 |
| `PYTHON_SERVICE_BASE_URL` | http://localhost:8000 |
| `python-service.connect-timeout` | 2s |
| `python-service.read-timeout` | 5s per internal request |
| Python `MODEL_TIMEOUT_SECONDS` | 1 second |
| Multipart file / request limit | 5 MiB / 25 MiB |
| Batch item limit | 20 |
| PDF pages / extracted characters | 50 / 100000 |

The model timeout should remain below Java's read timeout. Processing is sequential, so batch duration can exceed a single-item timeout. No application retries are used. The Java launcher disables the JDK HTTP client's automatic connection retry. A provider call is attempted at most once per supported question/item; conflicts and insufficient evidence do not call it.

## Caller identities

| X-Caller-Id | Tenant | Role |
|---|---|---|
| atlas-employee-01 | Atlas | employee |
| atlas-contractor-01 | Atlas | contractor |
| boreal-employee-01 | Boreal | employee |

This lookup simulates authentication as specified in the task. Missing/unknown callers are rejected. Tenant and role in uploaded text or public JSON never replace the lookup.

## Policy questions

`POST /answer`, `Content-Type: application/json`, `X-Caller-Id: atlas-employee-01`.

```json
{
  "question": "What is my annual certification reimbursement limit?",
  "as_of": "2026-09-21"
}
```

From the repository root:

```powershell
curl.exe -X POST http://localhost:8080/answer -H "Content-Type: application/json" -H "X-Caller-Id: atlas-employee-01" --data-binary "@examples/answer-request.json"
```

Business results use HTTP 200 and `{status, answer, citations}`. Each citation has `chunk_id` and a verbatim `quote`.

- `ANSWERED`: supported answer and eligible quotations.
- `INSUFFICIENT_EVIDENCE`: null answer and empty citations.
- `CONFLICT`: null answer and eligible quotations showing disagreement.

Policies are filtered by tenant, role, exact Approved state, and `effective_from <= as_of < effective_to`. Policy records are separate from code, unchanged from the supplied corpus. Exact duplicate ID/text pairs are deduplicated, and citations are sorted. Explicit amount and approval facts can complement each other; disagreement within a fact category produces conflict.

The vocabulary supports certification, home-office/home office, travel, training, and wellness/gym. Relevance requires a supported policy assertion, not merely a matching keyword. Amount questions require amount evidence. Individual payment, remaining-balance, and eligibility questions are conservatively unanswered because the supplied corpus cannot establish those conclusions.

## Batch intake

`POST /batches` is synchronous multipart/form-data with the same caller header.

- One `metadata` JSON part with Content-Type `application/json`.
- Repeated `files` parts, each with an original filename matching the manifest.
- One caller/date for the whole batch.
- Unique document IDs and filenames. IDs use letters, digits, underscores, and hyphens; filenames use letters, digits, dots, underscores, and hyphens without paths.
- Missing/extra files or duplicate manifest identifiers reject the entire batch before processing.

Example metadata:

```json
{
  "batch_id": "demo-01",
  "as_of": "2026-09-21",
  "documents": [
    {"document_id": "request-01", "filename": "request-01.txt"}
  ]
}
```

The full manifest is [examples/batch-metadata.json](examples/batch-metadata.json). All eight supplied documents are in [examples/requests](examples/requests). Request 02 is a real text-based PDF, 06 is a byte-for-byte copy of 01, and 08 is zero bytes.

Run the full demonstration from the repository root while both services are running:

```powershell
python scripts/demo.py
```

This calls both public endpoints, asserts the expected results, and saves actual response JSON in [examples/responses](examples/responses). Optional: `python scripts/demo.py --base-url http://localhost:8081`.

Expected mixed-batch outcomes:

| Item | Processing | Key finding |
|---|---|---|
| 01 | COMPLETED | INR 18000 requested; annual policy INR 25000; payable amount unresolved |
| 02 | COMPLETED | PDF extracted; INR 12000 vs INR 15000 policy conflict |
| 03 | COMPLETED | Amount null: INR 22000 vs INR 28000; policy itself answered |
| 04 | COMPLETED | Wellness policy insufficient evidence |
| 05 | COMPLETED | Embedded instructions do not switch Atlas to Boreal or approve the claim |
| 06 | COMPLETED | Separate result with duplicate_of request-01 |
| 07 | COMPLETED | Missing amount/currency; manager approval must be reviewed |
| 08 | FAILED | EMPTY_FILE; other items remain processed |

### Batch response shape

Top level: `batch_id`, `summary: {total, completed, failed}`, and `results` in manifest order.

Each result contains:

| Field | Shape / meaning |
|---|---|
| document_id | Manifest ID |
| processing_status | COMPLETED or FAILED |
| extracted | {benefit, amount, currency, reference}; null on failure |
| field_evidence | Same four keys, each an array of exact extracted-text quotations |
| policy | /answer response shape; null on failure or unresolved benefit |
| review_required | Always true |
| issues | Array of review-reason strings |
| duplicate_of | Earlier manifest document ID for identical file bytes; otherwise null |
| error | {code, message} on failure; otherwise null |

Amounts are **decimal strings**, e.g. `"18000"`, to avoid floating-point rounding. Missing/ambiguous extracted fields are null with empty field-evidence arrays. Ambiguous amount candidate quotations are retained in review reasons. Currency may remain known even when amount is ambiguous. PDF evidence quotes refer to extracted text, not PDF byte offsets.

A readable ambiguous document is COMPLETED and requires review. A parser, provider, or internal-service failure is FAILED. A batch with item failures still returns HTTP 200. Duplicate items are still independently processed and retain their own result; duplication never silently removes a submission.

### Postman

For /answer, use Body -> raw -> JSON and the caller header.

For /batches, use Body -> form-data:
1. Add `metadata` as Text; paste the manifest and set that row's Content-Type to `application/json`.
2. Add `files` as File and select all eight files (or repeat the files key).
3. Add `X-Caller-Id: atlas-employee-01`.
4. Let Postman generate the multipart Content-Type/boundary.

Do not set the entire batch request Content-Type to application/json.

## Errors

Public whole-request errors have `{code, message}`.

| HTTP / location | Codes |
|---|---|
| 400 | INVALID_CALLER, INVALID_REQUEST, INVALID_BATCH |
| 413 | UPLOAD_TOO_LARGE |
| 503 on /answer | PYTHON_SERVICE_FAILURE |
| Per-item error | EMPTY_FILE, UNREADABLE_FILE, NO_EXTRACTABLE_TEXT, UNSUPPORTED_FILE_TYPE, FILE_TOO_LARGE, DOCUMENT_TOO_LARGE |
| Per-item dependency error | PROVIDER_TIMEOUT, PROVIDER_UNAVAILABLE, MALFORMED_MODEL_OUTPUT, PYTHON_SERVICE_FAILURE |
| Other per-item failure | FILE_READ_FAILURE, PROCESSING_FAILURE |

Internal FastAPI validation errors return 422; internal answer-provider errors return 503. Java maps dependency failures to a safe public response. Neither is reported as insufficient policy evidence. Java also validates returned statuses, evidence structure, and answer/quotation consistency. A failed batch item's policy is null.

Application logs use batch/document IDs, status, and error code. They do not intentionally log raw uploaded text, amounts, or secrets. Keep verbose framework HTTP/body logging disabled when using sensitive data.

## Automated verification

```powershell
cd python-service
.\.venv\Scripts\python.exe -m pytest -q
cd ../spring-api
.\mvnw.cmd test
```

Tests cover policy access, dates, quotations, reordered/duplicated/changed records, evidence relevance, complementary rules, supplied TXT/PDF extraction, ambiguous fields, injection text, file errors, provider timeout/unavailability/malformed output, one-attempt behavior, Java HTTP serialization, multipart validation, duplicate preservation, failure isolation, and application startup.

The Python provider tests use controllable doubles; Java client tests use a local HTTP stub. The live `scripts/demo.py` separately verifies the real Java-to-Python path. No remote model service is required. Known gaps include arbitrary-language understanding, hostile PDF resource exhaustion, and production load; see [docs/DECISIONS.md](docs/DECISIONS.md).

Fixtures can be reproduced with `python scripts/create_fixtures.py`. This rewrites only the synthetic sample files and request JSON.

