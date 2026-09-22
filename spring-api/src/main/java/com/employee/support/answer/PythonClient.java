package com.employee.support.answer;

import java.net.http.HttpClient;
import java.time.Duration;
import com.employee.support.batch.InternalDocumentRequest;
import com.employee.support.batch.DocumentResult;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class PythonClient {

    private final RestClient restClient;

    public PythonClient(
        @Value("${python-service.base-url}") String baseUrl,
        @Value("${python-service.connect-timeout}") Duration connectTimeout,
        @Value("${python-service.read-timeout}") Duration readTimeout
    ) {
        HttpClient httpClient = HttpClient.newBuilder()
            // Use HTTP/1.1 for the Uvicorn service without an HTTP/2 upgrade attempt.
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(connectTimeout)
            .build();
        JdkClientHttpRequestFactory requestFactory = new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(readTimeout);

        this.restClient = RestClient.builder()
            .baseUrl(baseUrl)
            .requestFactory(requestFactory)
            .build();
    }

    public AnswerResponse answer(InternalAnswerRequest request) {
        try {
            AnswerResponse response = restClient.post()
                .uri("/internal/answer")
                .body(request)
                .retrieve()
                .body(AnswerResponse.class);

            if (response == null || !response.valid()) {
                throw new PythonServiceException("Python service returned an invalid response", null);
            }
            return response;
        } catch (PythonServiceException exception) {
            throw exception;
        } catch (RestClientException exception) {
            throw new PythonServiceException("Python service is unavailable or returned an invalid response", exception);
        }
    }

    public DocumentResult document(InternalDocumentRequest request) {
        try {
            DocumentResult response = restClient.post().uri("/internal/document").body(request)
                .retrieve().body(DocumentResult.class);
            if (response == null || !response.validFor(request.documentId())) {
                throw new PythonServiceException("Python service returned an invalid document result", null);
            }
            return response;
        } catch (RestClientException exception) {
            throw new PythonServiceException("Python service is unavailable or returned an invalid response", exception);
        }
    }
}
