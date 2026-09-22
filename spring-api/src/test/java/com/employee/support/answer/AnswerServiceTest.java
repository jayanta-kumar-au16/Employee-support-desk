package com.employee.support.answer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDate;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.employee.support.caller.CallerContextService;

class AnswerServiceTest {

    @Test
    void sendsTrustedCallerContextToPython() {
        PythonClient pythonClient = mock(PythonClient.class);
        AnswerResponse expected = new AnswerResponse(
            PolicyStatus.ANSWERED,
            "The annual certification reimbursement limit for employees is INR 25000.",
            List.of(new Citation("atlas-cert-current", "The annual certification reimbursement limit for employees is INR 25000."))
        );
        when(pythonClient.answer(any())).thenReturn(expected);
        AnswerService service = new AnswerService(new CallerContextService(), pythonClient);

        AnswerResponse actual = service.answer(
            "atlas-employee-01",
            new AnswerRequest("What is my certification limit?", LocalDate.of(2026, 9, 21))
        );

        ArgumentCaptor<InternalAnswerRequest> captor = ArgumentCaptor.forClass(InternalAnswerRequest.class);
        verify(pythonClient).answer(captor.capture());
        assertEquals("Atlas", captor.getValue().tenant());
        assertEquals("employee", captor.getValue().role());
        assertEquals(expected, actual);
    }
}
