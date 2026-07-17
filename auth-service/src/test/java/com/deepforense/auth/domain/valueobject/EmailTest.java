package com.deepforense.auth.domain.valueobject;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class EmailTest {

    @Test
    void acceptsInstitutionalEmailWithMultipleDomainLevels() {
        Email email = new Email("Paul@uce.edu.ec");

        assertEquals("paul@uce.edu.ec", email.value());
    }

    @Test
    void rejectsMalformedEmail() {
        assertThrows(IllegalArgumentException.class, () -> new Email("paul@uce"));
    }
}
