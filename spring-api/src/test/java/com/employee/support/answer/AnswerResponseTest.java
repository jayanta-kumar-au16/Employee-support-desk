package com.employee.support.answer;

import org.junit.jupiter.api.Test;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

class AnswerResponseTest {
    @Test void explanationDoesNotReplaceExactEvidenceValidation() {
        var citations = List.of(new Citation("p", "Policy text."));
        assertTrue(new AnswerResponse(PolicyStatus.ANSWERED, "Policy text.", citations, "Plain language explanation.").valid());
        assertFalse(new AnswerResponse(PolicyStatus.ANSWERED, "Invented answer.", citations, "Explanation.").valid());
        assertFalse(new AnswerResponse(PolicyStatus.INSUFFICIENT_EVIDENCE, null, List.of(), "Invented explanation.").valid());
        assertFalse(new AnswerResponse(PolicyStatus.ANSWERED, "Policy text.", citations, " ").valid());
    }
}
