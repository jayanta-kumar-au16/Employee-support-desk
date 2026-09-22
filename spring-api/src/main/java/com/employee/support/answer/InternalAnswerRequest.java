package com.employee.support.answer;

import java.time.LocalDate;

import com.fasterxml.jackson.annotation.JsonProperty;

public record InternalAnswerRequest(
    String tenant,
    String role,
    @JsonProperty("as_of") LocalDate asOf,
    String question
) {
}
