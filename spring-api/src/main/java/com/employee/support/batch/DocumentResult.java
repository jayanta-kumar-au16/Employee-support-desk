package com.employee.support.batch;

import java.util.List;
import java.util.Map;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.employee.support.answer.AnswerResponse;
import com.employee.support.error.ApiError;

public record DocumentResult(
    @JsonProperty("document_id") String documentId,
    @JsonProperty("processing_status") String processingStatus,
    Extracted extracted,
    @JsonProperty("field_evidence") Map<String, List<String>> fieldEvidence,
    AnswerResponse policy,
    @JsonProperty("review_required") Boolean reviewRequired,
    List<String> issues,
    @JsonProperty("duplicate_of") String duplicateOf,
    ApiError error
) {
    // Decimal string avoids rounding and retains the submitted monetary precision.
    public record Extracted(String benefit, String amount, String currency, String reference) {}

    public static DocumentResult failed(String id, String code, String message) {
        return new DocumentResult(id, "FAILED", null, Map.of("benefit", List.of(), "amount", List.of(),
            "currency", List.of(), "reference", List.of()), null, true,
            List.of("Human review is required; this report does not approve a claim or authorize payment."),
            null, new ApiError(code, message));
    }

    public DocumentResult withDuplicate(String earlierId) {
        return new DocumentResult(documentId, processingStatus, extracted, fieldEvidence, policy,
            reviewRequired, issues, earlierId, error);
    }

    public boolean validFor(String expectedId) {
        if (!expectedId.equals(documentId) || !Boolean.TRUE.equals(reviewRequired)
            || issues == null || issues.isEmpty() || issues.stream().anyMatch(s -> s == null || s.isBlank())
            || fieldEvidence == null || duplicateOf != null) return false;
        if (!fieldEvidence.keySet().equals(java.util.Set.of("benefit", "amount", "currency", "reference"))
            || fieldEvidence.values().stream().anyMatch(v -> v == null || v.stream().anyMatch(s -> s == null || s.isBlank()))) return false;
        if ("FAILED".equals(processingStatus)) {
            return extracted == null && policy == null && error != null
                && error.code() != null && !error.code().isBlank()
                && error.message() != null && !error.message().isBlank()
                && fieldEvidence.values().stream().allMatch(List::isEmpty);
        }
        if (!"COMPLETED".equals(processingStatus) || error != null || extracted == null) return false;
        if ((extracted.benefit() == null) != (policy == null) || (policy != null && !policy.valid())) return false;
        String[] names = {"benefit", "amount", "currency", "reference"};
        String[] values = {extracted.benefit(), extracted.amount(), extracted.currency(), extracted.reference()};
        for (int i = 0; i < names.length; i++) {
            if (values[i] == null ? !fieldEvidence.get(names[i]).isEmpty()
                : values[i].isBlank() || fieldEvidence.get(names[i]).isEmpty()) return false;
        }
        if (extracted.amount() != null && !extracted.amount().matches("[0-9]+(?:\\.[0-9]{1,2})?")) return false;
        return true;
    }
}
