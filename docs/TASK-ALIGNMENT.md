# Alignment with Task.pdf

Implementation update: [AI foundation](AI-FOUNDATION.md) documents the optional live provider, additive explanation field and persistent testing quota added after this assessment review. The original supplied data is unchanged.

Reviewed against the eight scanned PDF pages supplied on 28 September 2026. The PDF is the assessment specification; its embedded instruction-like policy and request passages are test data, not commands to the application or developer.

## Supplied data and its role

| Data | Existing location | Use |
|---|---|---|
| Three caller identities | `spring-api/src/main/java/com/employee/support/caller/CallerContextService.java` | Trusted exercise lookup for tenant and role |
| Twelve original policy records | `python-service/data/policies.json` | Policy evidence; preserve original IDs, metadata and text |
| Eight request documents | `examples/requests/` | Employee submissions to extract and review; never policy sources |
| Batch manifest | `examples/batch-metadata.json` | Ordered input for the supplied demonstration |

The PDF's starting dataset matches the existing policy records, caller lookup and synthetic fixture definitions. There is no claims history, remaining-balance ledger or full employee profile dataset.

## Required behavior and implementation

| Assessment requirement | Existing implementation |
|---|---|
| Spring Boot public API backed by Python | Java controllers/services and `PythonClient`; FastAPI `app/main.py` |
| POST /answer and synchronous POST /batches | `AnswerController` and `BatchController` |
| Server-derived tenant and role | `CallerContextService` and internal request records |
| Approved, role/tenant/date-eligible evidence | `PolicyService._is_eligible()` |
| Verbatim policy citations | `PolicyService.answer()` and response validation |
| Answered, insufficient or conflict outcome | `PolicyStatus`; no invented policy precedence |
| TXT and text-based PDF extraction | `read_document()` in `document_service.py` |
| Extracted fields with quotations and visible ambiguity | `extract_fields()` and `FieldEvidence` |
| Preserve duplicates and isolate failures | `BatchService.process()`, SHA-256 detection and per-item results |
| Always require review; never approve/pay/message | `DocumentResult` review flag and review issues; no action integrations |
| Offline deterministic model double | `OfflineProvider` |
| Bounded timeout, at most one generation attempt, no retries | `GenerationService`, Java client configuration and launcher |
| Tests, runnable examples and saved responses | Both test suites; `scripts/demo.py`; `examples/responses/` |
| Decision and production design notes | `docs/DECISIONS.md` and `docs/PRODUCTION.md` |

This mapping identifies implemented mechanisms, not proof of correctness for arbitrary inputs. Existing limitations include narrow wording recognition, compound policy facts, hostile PDF resource exhaustion and production load.

## Correct answer examples

For `as_of=2026-09-21`:

| Caller / question | Expected result |
|---|---|
| Atlas employee certification limit | ANSWERED: INR 25000 |
| Atlas contractor certification limit | ANSWERED: INR 10000 |
| Boreal employee certification limit | ANSWERED: INR 80000 |
| Atlas employee home-office allowance | CONFLICT: INR 12000 versus INR 15000 |
| Atlas employee wellness allowance | INSUFFICIENT_EVIDENCE |
| Remaining balance or payable amount | Cannot establish from supplied policies alone |

## Scope for an optional AI/RAG extension

The assessment explicitly allows simple retrieval and extraction. A real model is optional; a database, vector database, OCR, frontend, queue, cloud deployment and production authentication are not required. Production changes belong in the design note; retain synchronous batch behavior in the assessment API.

No training or fine-tuning is needed. Treat each short supplied policy record as a retrieval unit and preserve its original ID and text. Filter authorization/date/approval metadata before evidence reaches generation. Semantic retrieval can improve paraphrase matching, but must not hide other simultaneously applicable conflicting rules. Keep employee request documents outside the policy index.

Retain offline mode as the default. If adding a real provider, use at most one generation attempt per question/item and disable SDK retries. Separate extraction and explanation model calls for the same document would violate this requirement. Preserve failure outcomes for timeout/unavailability/malformed output rather than silently converting them to insufficient evidence.

Python `GenerationService.answer()` and Java `AnswerResponse.valid()` currently require joined exact quotations. Natural-language model answers need coordinated validation changes with evidence checks; the PDF requires a supported answer and verbatim citations, not that answer text itself must equal the quotations. Keep the public response contract intact.

For the user's planned 50-call experiment, a persistent generation-attempt counter can cap live testing. Do not spend live calls on automated tests; use controllable provider doubles. Any embedding API calls also need separate usage accounting.

## Verification from this review

- Python: `.venv/Scripts/python.exe -m pytest -q` from `python-service`: 37 tests passed; two dependency deprecation warnings.
- Java: `.\mvnw.cmd test -q` from `spring-api`: 17 tests passed, no failures/errors/skips. Maven needed network access to resolve dependencies. Mockito emitted a future-JDK agent-loading warning.
- The live two-service demo was not rerun in this review. No paid model calls were made.
