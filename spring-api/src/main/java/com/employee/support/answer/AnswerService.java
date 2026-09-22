package com.employee.support.answer;

import org.springframework.stereotype.Service;

import com.employee.support.caller.CallerContext;
import com.employee.support.caller.CallerContextService;

@Service
public class AnswerService {

    private final CallerContextService callerContextService;
    private final PythonClient pythonClient;

    public AnswerService(CallerContextService callerContextService, PythonClient pythonClient) {
        this.callerContextService = callerContextService;
        this.pythonClient = pythonClient;
    }

    public AnswerResponse answer(String callerId, AnswerRequest request) {
        CallerContext caller = callerContextService.requireKnownCaller(callerId);
        InternalAnswerRequest internalRequest = new InternalAnswerRequest(
            caller.tenant(),
            caller.role(),
            request.asOf(),
            request.question()
        );
        return pythonClient.answer(internalRequest);
    }
}
