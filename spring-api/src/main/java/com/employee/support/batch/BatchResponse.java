package com.employee.support.batch;

import java.util.List;
import com.fasterxml.jackson.annotation.JsonProperty;

public record BatchResponse(@JsonProperty("batch_id") String batchId, Summary summary, List<DocumentResult> results) {
    public record Summary(int total, int completed, int failed) {}
}
