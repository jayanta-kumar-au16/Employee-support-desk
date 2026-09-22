package com.employee.support.caller;

import java.util.Map;

import org.springframework.stereotype.Service;

@Service
public class CallerContextService {

    private static final Map<String, CallerContext> CALLERS = Map.of(
        "atlas-employee-01", new CallerContext("atlas-employee-01", "Atlas", "employee"),
        "atlas-contractor-01", new CallerContext("atlas-contractor-01", "Atlas", "contractor"),
        "boreal-employee-01", new CallerContext("boreal-employee-01", "Boreal", "employee")
    );

    public CallerContext requireKnownCaller(String callerId) {
        if (callerId == null || callerId.isBlank()) {
            throw new UnknownCallerException();
        }

        CallerContext context = CALLERS.get(callerId);
        if (context == null) {
            throw new UnknownCallerException();
        }
        return context;
    }
}
