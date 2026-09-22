package com.employee.support.error;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.employee.support.answer.PythonServiceException;
import com.employee.support.caller.UnknownCallerException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(UnknownCallerException.class)
    public ResponseEntity<ApiError> unknownCaller(UnknownCallerException exception) {
        return ResponseEntity.badRequest()
            .body(new ApiError("INVALID_CALLER", exception.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiError> invalidBody(MethodArgumentNotValidException exception) {
        return ResponseEntity.badRequest()
            .body(new ApiError("INVALID_REQUEST", "question must be non-empty and as_of must be provided"));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiError> unreadableBody(HttpMessageNotReadableException exception) {
        return ResponseEntity.badRequest()
            .body(new ApiError("INVALID_REQUEST", "Request JSON or as_of date is invalid"));
    }

    @ExceptionHandler(PythonServiceException.class)
    public ResponseEntity<ApiError> dependencyFailure(PythonServiceException exception) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
            .body(new ApiError("PYTHON_SERVICE_FAILURE", "The answer service is temporarily unavailable"));
    }
}
