# Production design note

For 10,000 requests per day containing personal information, I would deploy the Java API and Python workers as separate containers on a managed container platform in a private network. Use managed identity/secrets, a managed database for batch state and audit events, and encrypted object storage with short retention for uploaded files. Keep the policy corpus versioned and record the version used for every result.

Replace the synchronous batch path with durable jobs and a status endpoint. A queue and bounded worker concurrency absorb bursts and isolate slow document processing. Preserve idempotency keys and per-item state so redelivery cannot create duplicate actions. Retain the human-review boundary; this system must not approve or pay claims automatically.

Replace the simulated caller header with verified organization identity and authorization. Derive tenant/role from trusted claims, enforce tenant isolation in storage and retrieval, and authenticate internal service calls. Apply upload limits, malware screening, and process isolation for parsers. Treat documents and model output as untrusted, validate evidence and response schemas, and prevent document text from changing authorization or workflow.

Use an adapter for the slow approval system with bounded timeouts, explicit failure states, a circuit breaker, and documented idempotency behavior. Avoid automatic retries of uncertain side effects until the external system's guarantees are understood. Reviewers should see stale or unavailable approval information explicitly.

Monitor queue age, throughput, parsing failures, provider latency, and downstream availability. Use batch/document correlation IDs, access-controlled audit logs, and redacted diagnostics rather than raw document contents. Establish deletion, backup, incident-response, and recovery procedures.

Before committing to a delivery date, clarify peak load, file sizes/types/languages, retention and residency obligations, role mappings, policy ownership and precedence, review SLAs, approval-system authentication/rate limits/sandbox availability, supported operations, and behavior when requests time out after possible acceptance. Confirm acceptable extraction accuracy and the reviewer escalation process with representative synthetic data.
