package com.employee.support.error;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import com.employee.support.answer.PythonServiceException;
import com.employee.support.caller.UnknownCallerException;
import com.employee.support.batch.InvalidBatchException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.MultipartException;

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
            .body(new ApiError("INVALID_REQUEST", "Request fields are missing or invalid; check the API contract"));
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

    @ExceptionHandler(InvalidBatchException.class)
    public ResponseEntity<ApiError> invalidBatch(InvalidBatchException exception) {
        return ResponseEntity.badRequest().body(new ApiError("INVALID_BATCH", exception.getMessage()));
    }

    @ExceptionHandler(MissingServletRequestPartException.class)
    public ResponseEntity<ApiError> missingPart(MissingServletRequestPartException exception) {
        return ResponseEntity.badRequest().body(new ApiError("INVALID_BATCH", "metadata and files multipart parts are required"));
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ApiError> uploadTooLarge(MaxUploadSizeExceededException exception) {
        return ResponseEntity.status(413).body(new ApiError("UPLOAD_TOO_LARGE", "Upload exceeds the configured size limit"));
    }

    @ExceptionHandler(MultipartException.class)
    public ResponseEntity<ApiError> invalidMultipart(MultipartException exception) {
        return ResponseEntity.badRequest().body(new ApiError("INVALID_BATCH", "Multipart request could not be read"));
    }
}
