package com.employee.support.answer;

import java.util.List;

public record AnswerResponse(
    PolicyStatus status,
    String answer,
    List<Citation> citations
) {
    public boolean valid() {
        if (status == null || citations == null || citations.stream().anyMatch(c -> c == null
            || c.chunkId() == null || c.chunkId().isBlank() || c.quote() == null || c.quote().isBlank())) return false;
        return switch (status) {
            case ANSWERED -> answer != null && !answer.isBlank() && !citations.isEmpty()
                && answer.equals(citations.stream().map(Citation::quote).distinct().collect(java.util.stream.Collectors.joining(" ")));
            case INSUFFICIENT_EVIDENCE -> answer == null && citations.isEmpty();
            case CONFLICT -> answer == null && citations.stream().map(Citation::quote).distinct().count() >= 2;
        };
    }
}
