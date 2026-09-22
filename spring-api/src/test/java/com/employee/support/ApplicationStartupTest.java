package com.employee.support;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ApplicationStartupTest {
    @Test void startsWithAllControllersAndClientConfiguration() {}
}
