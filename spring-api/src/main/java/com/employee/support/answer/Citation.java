package com.employee.support.answer;

import com.fasterxml.jackson.annotation.JsonProperty;

public record Citation(
    @JsonProperty("chunk_id") String chunkId,
    String quote
) {
}
