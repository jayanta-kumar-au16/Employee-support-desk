package com.employee.support.answer;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid;

@RestController
public class AnswerController {

    private final AnswerService answerService;

    public AnswerController(AnswerService answerService) {
        this.answerService = answerService;
    }

    @PostMapping("/answer")
    public ResponseEntity<AnswerResponse> answer(
        @RequestHeader(value = "X-Caller-Id", required = false) String callerId,
        @Valid @RequestBody AnswerRequest request
    ) {
        return ResponseEntity.ok(answerService.answer(callerId, request));
    }
}
