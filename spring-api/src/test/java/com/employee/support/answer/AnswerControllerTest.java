package com.employee.support.answer;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.employee.support.caller.UnknownCallerException;
import com.employee.support.error.GlobalExceptionHandler;

class AnswerControllerTest {

    private AnswerService answerService;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        answerService = mock(AnswerService.class);
        mockMvc = MockMvcBuilders
            .standaloneSetup(new AnswerController(answerService))
            .setControllerAdvice(new GlobalExceptionHandler())
            .build();
    }

    @Test
    void returnsSupportedAnswer() throws Exception {
        when(answerService.answer(eq("atlas-employee-01"), any())).thenReturn(
            new AnswerResponse(
                PolicyStatus.ANSWERED,
                "The annual certification reimbursement limit for employees is INR 25000.",
                List.of(new Citation("atlas-cert-current", "The annual certification reimbursement limit for employees is INR 25000."))
            )
        );

        mockMvc.perform(post("/answer")
                .header("X-Caller-Id", "atlas-employee-01")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"question":"What is my certification limit?","as_of":"2026-09-21"}
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("ANSWERED"))
            .andExpect(jsonPath("$.citations[0].chunk_id").value("atlas-cert-current"));
    }

    @Test
    void rejectsEmptyQuestion() throws Exception {
        mockMvc.perform(post("/answer")
                .header("X-Caller-Id", "atlas-employee-01")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"question":"   ","as_of":"2026-09-21"}
                    """))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }

    @Test
    void rejectsMissingCaller() throws Exception {
        when(answerService.answer(eq(null), any())).thenThrow(new UnknownCallerException());

        mockMvc.perform(post("/answer")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"question":"What is my certification limit?","as_of":"2026-09-21"}
                    """))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("INVALID_CALLER"));
    }

    @Test
    void rejectsInvalidDateFormat() throws Exception {
        mockMvc.perform(post("/answer")
                .header("X-Caller-Id", "atlas-employee-01")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"question":"What is my certification limit?","as_of":"21-09-2026"}
                    """))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }
}
