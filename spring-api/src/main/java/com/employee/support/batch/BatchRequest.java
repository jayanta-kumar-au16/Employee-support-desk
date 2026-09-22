package com.employee.support.batch;

import java.time.LocalDate;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record BatchRequest(
    @JsonProperty("batch_id") @NotNull @Pattern(regexp = "[A-Za-z0-9_-]{1,100}") String batchId,
    @JsonProperty("as_of") @NotNull LocalDate asOf,
    @NotNull @Size(min = 1, max = 20) List<@NotNull @Valid Entry> documents
) {
    public record Entry(
        @JsonProperty("document_id") @NotNull @Pattern(regexp = "[A-Za-z0-9_-]{1,100}") String documentId,
        @NotNull @Pattern(regexp = "[A-Za-z0-9][A-Za-z0-9._-]{0,199}") String filename
    ) {}
}
