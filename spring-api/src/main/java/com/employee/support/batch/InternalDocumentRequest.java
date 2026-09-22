package com.employee.support.batch;

import java.time.LocalDate;
import com.fasterxml.jackson.annotation.JsonProperty;

public record InternalDocumentRequest(
    String tenant,
    String role,
    @JsonProperty("as_of") LocalDate asOf,
    @JsonProperty("batch_id") String batchId,
    @JsonProperty("document_id") String documentId,
    String filename,
    @JsonProperty("content_base64") String contentBase64
) {}
