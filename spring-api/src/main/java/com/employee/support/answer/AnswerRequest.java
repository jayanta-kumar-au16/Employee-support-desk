package com.employee.support.answer;

import java.time.LocalDate;

import com.fasterxml.jackson.annotation.JsonProperty;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record AnswerRequest(
    @NotBlank String question,
    @NotNull @JsonProperty("as_of") LocalDate asOf
) {
}
