package com.employee.support.answer;

import static org.junit.jupiter.api.Assertions.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.LocalDate;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import com.employee.support.batch.InternalDocumentRequest;

class PythonClientTest {
    private InternalAnswerRequest request() {
        return new InternalAnswerRequest("Atlas", "employee", LocalDate.of(2026, 9, 21), "certification limit");
    }

    @Test void serializesContractAndUsesHttp11() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        AtomicReference<String> received = new AtomicReference<>();
        AtomicReference<String> upgrade = new AtomicReference<>();
        server.createContext("/internal/answer", exchange -> {
            received.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            upgrade.set(exchange.getRequestHeaders().getFirst("Upgrade"));
            byte[] body = """
                {"status":"ANSWERED","answer":"Policy text.","citations":[{"chunk_id":"p","quote":"Policy text."}]}
                """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();
        try {
            var client = new PythonClient("http://127.0.0.1:" + server.getAddress().getPort(), Duration.ofSeconds(1), Duration.ofSeconds(2));
            assertEquals(PolicyStatus.ANSWERED, client.answer(request()).status());
            assertTrue(received.get().contains("\"as_of\":\"2026-09-21\""));
            assertTrue(received.get().contains("\"tenant\":\"Atlas\""));
            assertNull(upgrade.get());
        } finally { server.stop(0); }
    }

    @Test void rejectsMalformedAndUnsupportedResponsesWithoutRetries() throws Exception {
        for (String response : new String[]{"not json", "{}", "null", "{\"status\":\"ANSWERED\",\"answer\":\"invented\",\"citations\":[]}"}) {
            AtomicInteger calls = new AtomicInteger();
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/", exchange -> {
                calls.incrementAndGet();
                exchange.getRequestBody().readAllBytes();
                byte[] body = response.getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, body.length);
                exchange.getResponseBody().write(body);
                exchange.close();
            });
            server.start();
            try {
                var client = new PythonClient("http://127.0.0.1:" + server.getAddress().getPort(), Duration.ofSeconds(1), Duration.ofSeconds(2));
                assertThrows(PythonServiceException.class, () -> client.answer(request()));
                assertThrows(PythonServiceException.class, () -> client.document(new InternalDocumentRequest("Atlas", "employee", LocalDate.now(), "b", "d", "d.txt", "")));
                assertEquals(2, calls.get());
            } finally { server.stop(0); }
        }
    }

    @Test void dependencyTimeoutAndUnavailableAreTechnicalFailures() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        AtomicInteger calls = new AtomicInteger();
        server.createContext("/", exchange -> {
            calls.incrementAndGet();
            try { Thread.sleep(500); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
            exchange.close();
        });
        server.start();
        int port = server.getAddress().getPort();
        var client = new PythonClient("http://127.0.0.1:" + port, Duration.ofMillis(200), Duration.ofMillis(100));
        try {
            assertThrows(PythonServiceException.class, () -> client.answer(request()));
            assertEquals(1, calls.get());
        } finally { server.stop(0); }
        assertThrows(PythonServiceException.class, () -> client.answer(request()));
    }
}

