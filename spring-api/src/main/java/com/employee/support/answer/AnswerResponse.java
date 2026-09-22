package com.employee.support.answer;

import java.util.List;

public record AnswerResponse(
    PolicyStatus status,
    String answer,
    List<Citation> citations
) {
}
