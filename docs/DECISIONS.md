# Implementation decisions and disclosure

## Evidence first, with an offline model double

The consequential choice is to filter policy metadata and select supported facts before generation. Only approved, tenant/role/date-eligible evidence enters the provider. The offline provider returns exact quotations; its output must match those quotations before it is accepted. Provider output cannot select identity, change status, approve claims, or create policy evidence. Conflict and insufficient-evidence outcomes need zero generation attempts; a supported answer uses exactly one. There are no application-level retries, and the Java launcher disables JDK connection retries.

An alternative was an LLM receiving all policies and deciding which ones apply. That would make access isolation and reproducibility harder, would introduce a paid/network dependency, and would need stronger output evaluation. A real model is optional in the assignment and is not integrated here.

## Main limitations

The deterministic vocabulary and fact rules are intentionally small. They handle the supplied data and variations covered by tests, but do not understand arbitrary language, all currencies, all PDF layouts, or every logically equivalent/contradictory wording. Unknown policy assertions are excluded rather than guessed. Different nonnumeric statements within the same fact category are conservatively treated as conflicts. A mixed payment-and-limit question is conservatively unanswered; batch reports instead separate extracted data, policy terms, and review reasons.

Amounts are decimal strings; missing or ambiguous fields are null. Quotes are exact substrings of extracted document text; PDF whitespace can differ from visual layout. TXT/PDF parsing is local, and documents are never policy sources. The service does not infer an amount from a bare number without a supported currency prefix. No OCR, claims-history lookup, payment calculation, real authentication, or external approval-system integration is implemented.

The provider timeout bounds waiting and outstanding workers, but cannot forcibly kill an already-running Python thread. The bundled provider is local and terminating. A future remote provider must also enforce transport timeouts; untrusted parsers/providers should run in isolated processes in production. Parser resource limits are basic, not a hardened hostile-file sandbox.

## Time spent and AI assistance

- Candidate time spent: **TO BE FILLED BY THE CANDIDATE before submission.** This cannot be inferred from repository history or invented by the assistant.
- AI assistance: Codex assisted with the Java/Python implementation, debugging, test creation, synthetic fixture generation, demo tooling, and documentation. The candidate is responsible for reviewing and understanding the final implementation and reporting their own contribution accurately.
- Required workflow implementation: both public endpoints and the supplied mixed batch are implemented. Remaining submission work is to fill in the personal time statement, review the code/notes, publish the chosen commit, and provide its full SHA. Optional real-model and production integrations are not implemented.
- Coverage gap: tests do not exhaust arbitrary prose, adversarial PDF resource exhaustion, every PDF font/layout, high concurrent load, or integration with a real model/approval system.
