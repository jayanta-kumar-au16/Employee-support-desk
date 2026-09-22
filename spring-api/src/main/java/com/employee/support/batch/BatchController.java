package com.employee.support.batch;

import java.util.List;
import jakarta.validation.Valid;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
public class BatchController {
    private final BatchService service;

    public BatchController(BatchService service) { this.service = service; }

    @PostMapping(value = "/batches", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BatchResponse batches(
        @RequestHeader(value = "X-Caller-Id", required = false) String callerId,
        @Valid @RequestPart("metadata") BatchRequest metadata,
        @RequestPart("files") List<MultipartFile> files
    ) {
        return service.process(callerId, metadata, files);
    }
}
