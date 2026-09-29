# Policy retrieval (RAG)

The Python service uses local lexical retrieval-augmented generation. No new
dependencies, embeddings, vector database, or indexing command are required.
The public API request and response formats are unchanged.

## Flow

1. Spring resolves the caller's tenant and role.
2. Python identifies one supported benefit using explicit terms and controlled
   synonyms. Ambiguous benefits and personal balance/payment questions remain
   insufficient evidence.
3. `PolicyRetriever` reads `python-service/data/policies.json`. Each short policy
   record is a source chunk with an ID, text, and access/effective-date metadata.
4. Before indexing, it filters by tenant, role, exact Approved state, and
   `effective_from <= as_of < effective_to`, and excludes unsupported policy text.
5. It builds an in-memory lexical index and ranks matching benefit chunks with
   BM25 (term frequency and document-length normalization). Controlled benefit
   synonyms add canonical search tokens to both queries and source text.
6. All matching applicable rules are retained, including lower-ranked evidence.
   There is deliberately no top-k cutoff that could hide contradictory rules.
   Amount and approval questions additionally require the corresponding fact type.
7. The policy service detects conflicts before generation. Public citations remain
   sorted by source ID/text, and the answer remains exact source quotations.
8. In live mode, the existing OpenAI provider explains the retrieved evidence.
   Offline mode returns the extractive answer with a null explanation. Neither
   conflicts nor missing evidence trigger a model call.

BM25 background: [Stanford Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html).

## Try it

Restart Python after updating the code. Use `POST http://localhost:8080/answer`
with `Content-Type: application/json` and `X-Caller-Id: atlas-employee-01`:

```json
{
  "question": "What is my professional exam reimbursement limit?",
  "as_of": "2026-09-21"
}
```

Expected: `ANSWERED`, INR 25000, citation `atlas-cert-current`.

| Question (same caller and date) | Expected result |
|---|---|
| What allowance applies to working from home? | CONFLICT: INR 12000 and INR 15000 |
| Explain the policy for business trips | ANSWERED: rail travel for approved business trips |
| Do external courses require approval? | ANSWERED: manager approval before booking |
| What is my external course budget? | INSUFFICIENT_EVIDENCE: no amount rule |
| What is my fitness membership limit? | INSUFFICIENT_EVIDENCE: no policy |

## Scope and limits

This is lexical RAG with a controlled synonym vocabulary, not unrestricted semantic
search. It retains the existing supported fact parser; arbitrary handbook prose
may need additional extraction rules. No PDF ingestion or document upload endpoint
for policies is introduced. Employee reimbursement uploads remain untrusted input
and never enter the policy corpus. Both answer requests and batch policy lookups
use the retriever, while batch field extraction keeps its existing vocabulary.

Policy records are read and the small eligible index is rebuilt on every request,
so edits become visible without reindexing. This is suitable for the current small
corpus. A large collection would need a persistent index with update handling,
authorization-aware search, and a way to retrieve complete conflicting rule groups.
Ranking scores are internal relevance scores, not confidence in policy correctness.

No live model calls are needed to test retrieval. Run from `python-service`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
