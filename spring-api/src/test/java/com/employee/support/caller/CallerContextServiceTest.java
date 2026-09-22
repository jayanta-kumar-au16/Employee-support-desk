package com.employee.support.caller;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class CallerContextServiceTest {

    private final CallerContextService service = new CallerContextService();

    @Test
    void resolvesTrustedTenantAndRole() {
        CallerContext context = service.requireKnownCaller("atlas-employee-01");

        assertEquals("Atlas", context.tenant());
        assertEquals("employee", context.role());
    }

    @Test
    void rejectsUnknownCaller() {
        assertThrows(UnknownCallerException.class, () -> service.requireKnownCaller("not-known"));
    }

    @Test
    void rejectsMissingCaller() {
        assertThrows(UnknownCallerException.class, () -> service.requireKnownCaller(null));
    }
}
