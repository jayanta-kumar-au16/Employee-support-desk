package com.employee.support;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class SpringApiApplication {

    public static void main(String[] args) {
        // Set before JDK HttpClient initializes; no transparent connection retries.
        System.setProperty("jdk.httpclient.disableRetryConnect", "true");
        SpringApplication.run(SpringApiApplication.class, args);
    }
}
