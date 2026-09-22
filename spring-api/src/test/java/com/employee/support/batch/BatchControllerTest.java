package com.employee.support.batch;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import com.employee.support.answer.*;
import com.employee.support.caller.CallerContextService;
import com.employee.support.error.GlobalExceptionHandler;

class BatchControllerTest {
    private PythonClient python;
    private MockMvc mvc;

    @BeforeEach void setup() {
        python = mock(PythonClient.class);
        mvc = MockMvcBuilders.standaloneSetup(new BatchController(new BatchService(new CallerContextService(), python)))
            .setControllerAdvice(new GlobalExceptionHandler()).build();
    }

    private MockMultipartFile metadata(String json) {
        return new MockMultipartFile("metadata", "metadata.json", "application/json", json.getBytes(StandardCharsets.UTF_8));
    }

    private MockMultipartFile file(String name, String content) {
        return new MockMultipartFile("files", name, "text/plain", content.getBytes(StandardCharsets.UTF_8));
    }

    @Test void mixedResultsKeepOrderAndDuplicateAndContinueAfterDependencyFailure() throws Exception {
        when(python.document(any())).thenAnswer(invocation -> {
            InternalDocumentRequest request = invocation.getArgument(0);
            assertEquals("Atlas", request.tenant());
            assertEquals("employee", request.role());
            if (request.documentId().equals("b")) throw new PythonServiceException("private details", null);
            return new DocumentResult(request.documentId(), "COMPLETED",
                new DocumentResult.Extracted(null, null, null, null), Map.of(), null, true,
                List.of("Human review required"), null, null);
        });
        mvc.perform(multipart("/batches").file(metadata("""
            {"batch_id":"demo","as_of":"2026-09-21","tenant":"Boreal","documents":[
            {"document_id":"a","filename":"a.txt"},
            {"document_id":"b","filename":"b.txt"},
            {"document_id":"c","filename":"c.txt"}]}
            """))
            .file(file("c.txt", "same")).file(file("b.txt", "different")).file(file("a.txt", "same"))
            .header("X-Caller-Id", "atlas-employee-01"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.summary.total").value(3))
            .andExpect(jsonPath("$.summary.completed").value(2))
            .andExpect(jsonPath("$.summary.failed").value(1))
            .andExpect(jsonPath("$.results[0].document_id").value("a"))
            .andExpect(jsonPath("$.results[1].error.code").value("PYTHON_SERVICE_FAILURE"))
            .andExpect(jsonPath("$.results[2].duplicate_of").value("a"))
            .andExpect(jsonPath("$.results[2].review_required").value(true));
        verify(python, times(3)).document(any());
    }

    @Test void duplicateManifestIdentifiersFailBeforeProcessing() throws Exception {
        mvc.perform(multipart("/batches").file(metadata("""
            {"batch_id":"demo","as_of":"2026-09-21","documents":[
            {"document_id":"a","filename":"a.txt"},{"document_id":"a","filename":"b.txt"}]}
            """))
            .file(file("a.txt", "x")).file(file("b.txt", "y")).header("X-Caller-Id", "atlas-employee-01"))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_BATCH"));
        verifyNoInteractions(python);
    }

    @Test void missingExtraAndDuplicateUploadsFailBeforeProcessing() throws Exception {
        String manifest = """
            {"batch_id":"demo","as_of":"2026-09-21","documents":[{"document_id":"a","filename":"a.txt"}]}
            """;
        for (String extra : List.of("other.txt", "a.txt")) {
            mvc.perform(multipart("/batches").file(metadata(manifest)).file(file("a.txt", "x"))
                .file(file(extra, "y")).header("X-Caller-Id", "atlas-employee-01"))
                .andExpect(status().isBadRequest());
        }
        mvc.perform(multipart("/batches").file(metadata(manifest)).file(file("other.txt", "x"))
            .header("X-Caller-Id", "atlas-employee-01")).andExpect(status().isBadRequest());
        verifyNoInteractions(python);
    }

    @Test void rejectsInvalidMetadataAndUnknownCaller() throws Exception {
        for (String manifest : List.of("{}", """
            {"batch_id":"demo","as_of":"2026-09-21","documents":[{"document_id":"a","filename":"../a.txt"}]}
            """, """
            {"batch_id":"demo","as_of":"21-09-2026","documents":[]}
            """)) {
            mvc.perform(multipart("/batches").file(metadata(manifest)).file(file("a.txt", "x"))
                .header("X-Caller-Id", "atlas-employee-01")).andExpect(status().isBadRequest());
        }
        mvc.perform(multipart("/batches").file(metadata("""
            {"batch_id":"demo","as_of":"2026-09-21","documents":[{"document_id":"a","filename":"a.txt"}]}
            """ )).file(file("a.txt", "x")).header("X-Caller-Id", "unknown"))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_CALLER"));
        verifyNoInteractions(python);
    }

    @Test void rejectsMissingMultipartParts() throws Exception {
        mvc.perform(multipart("/batches").file(file("a.txt", "x")).header("X-Caller-Id", "atlas-employee-01"))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_BATCH"));
    }
}
