package com.employee.support.batch;

import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import com.employee.support.answer.PythonClient;
import com.employee.support.answer.PythonServiceException;
import com.employee.support.caller.CallerContextService;

@Service
public class BatchService {
    private static final Logger LOG = LoggerFactory.getLogger(BatchService.class);
    private final CallerContextService callers;
    private final PythonClient python;

    public BatchService(CallerContextService callers, PythonClient python) {
        this.callers = callers;
        this.python = python;
    }

    public BatchResponse process(String callerId, BatchRequest metadata, List<MultipartFile> files) {
        var caller = callers.requireKnownCaller(callerId);
        Map<String, MultipartFile> uploads = new HashMap<>();
        Set<String> ids = new HashSet<>();
        Set<String> filenames = new HashSet<>();
        for (var entry : metadata.documents()) {
            if (!ids.add(entry.documentId()) || !filenames.add(entry.filename())) {
                throw new InvalidBatchException("Manifest document IDs and filenames must be unique");
            }
        }
        for (var file : files) {
            if (file.getOriginalFilename() == null || uploads.putIfAbsent(file.getOriginalFilename(), file) != null) {
                throw new InvalidBatchException("Each uploaded filename must appear exactly once");
            }
        }
        if (!uploads.keySet().equals(filenames)) {
            throw new InvalidBatchException("Uploaded filenames must exactly match the manifest");
        }
        List<DocumentResult> results = new ArrayList<>();
        Map<String, String> firstDocumentByHash = new HashMap<>();
        for (var entry : metadata.documents()) {
            DocumentResult result;
            String duplicateOf = null;
            try {
                byte[] bytes = uploads.get(entry.filename()).getBytes();
                String hash = digest(bytes);
                duplicateOf = firstDocumentByHash.putIfAbsent(hash, entry.documentId());
                // Each manifest entry remains a result, including duplicate and failed files.
                result = python.document(new InternalDocumentRequest(caller.tenant(), caller.role(), metadata.asOf(),
                    metadata.batchId(), entry.documentId(), entry.filename(), Base64.getEncoder().encodeToString(bytes)));
            } catch (IOException exception) {
                result = DocumentResult.failed(entry.documentId(), "FILE_READ_FAILURE", "The uploaded file could not be read");
            } catch (PythonServiceException exception) {
                result = DocumentResult.failed(entry.documentId(), "PYTHON_SERVICE_FAILURE", "The document service is temporarily unavailable or returned an invalid response");
            }
            if (duplicateOf != null) result = result.withDuplicate(duplicateOf);
            results.add(result);
            LOG.info("batch={} document={} status={} error={}", metadata.batchId(), entry.documentId(),
                result.processingStatus(), result.error() == null ? "none" : result.error().code());
        }
        int completed = (int) results.stream().filter(r -> "COMPLETED".equals(r.processingStatus())).count();
        return new BatchResponse(metadata.batchId(), new BatchResponse.Summary(results.size(), completed, results.size() - completed), results);
    }

    private static String digest(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (NoSuchAlgorithmException exception) { throw new IllegalStateException(exception); }
    }
}
