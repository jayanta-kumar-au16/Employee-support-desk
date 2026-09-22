# Implementation decisions and disclosure

## Evidence first, with an offline model double

The consequential choice is to filter policy metadata and select supported facts before generation. Only approved, tenant/role/date-eligible evidence enters the provider. The offline provider joins distinct, exact policy quotations with spaces; validation accepts only an object containing a single `answer` field equal to that expected text. Caller identity, policy status, and citations are determined outside the provider; its output cannot approve claims or create policy evidence. Conflict and insufficient-evidence outcomes make zero generation attempts; a successful supported answer uses exactly one. Capacity exhaustion can reject a request before generation starts. There are no application-level retries, and the Java launcher disables JDK HTTP-client connection retries.

An alternative was an LLM receiving all policies and deciding which ones apply. That would make access isolation and reproducibility harder and would need stronger output evaluation. A hosted model could also introduce network and usage-cost dependencies. A real model is optional in the assignment and is not integrated here.

## Main limitations

The deterministic vocabulary and fact rules are intentionally small. They handle the supplied data and variations covered by tests, but do not understand arbitrary language, all currencies, all PDF layouts, or every logically equivalent/contradictory wording. Policy chunks without a recognized fact are excluded. Each chunk is classified into at most one fact category, and amount matching uses the first recognized currency-qualified amount; compound assertions and multiple limits within one chunk are not fully analyzed. Different nonnumeric statements within the same fact category are conservatively treated as conflicts after case and whitespace normalization. A mixed payment-and-limit question containing a recognized payment term is conservatively unanswered; batch reports instead separate extracted data, policy terms, and review reasons.

Amounts are decimal strings; missing or ambiguous fields are null. Quotes are exact substrings of extracted document text; PDF whitespace can differ from visual layout. TXT/PDF parsing is local, and documents are never policy sources. The service does not infer an amount from a bare number without a supported currency prefix. No OCR, claims-history lookup, payment calculation, real authentication, or external approval-system integration is implemented.

The provider timeout bounds how long a request waits for generation; a shared four-slot limit bounds outstanding provider calls per Python process. A timeout cannot forcibly kill an already-running Python thread, which retains its slot until it finishes. The bundled provider is local and terminating. A future remote provider must also enforce transport timeouts; untrusted parsers/providers should run in isolated processes in production. Parser resource limits are basic, not a hardened hostile-file sandbox.

## Time spent and AI assistance

- Candidate-reported time spent: Approximately 8 hours, including implementation, debugging, testing, and documentation.
- AI assistance: Codex assisted with the Java/Python implementation, debugging, test creation, synthetic fixture generation, demo tooling, and documentation. The candidate is responsible for reviewing and understanding the final implementation and reporting their own contribution accurately.
- Required workflow implementation: both public endpoints and the supplied mixed batch are implemented. Remaining submission work is to review the code and notes, publish the chosen commit, and provide its full SHA. Optional real-model and production integrations are not implemented.
- Coverage gap: tests do not exhaust arbitrary prose, adversarial PDF resource exhaustion, every PDF font/layout, high concurrent load, or integration with a real model/approval system.
