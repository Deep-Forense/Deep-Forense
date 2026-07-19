package com.deepforense.auth.domain.valueobject;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class RawPasswordTest {

    @Test
    void acceptsPasswordWithMinimumLength() {
        RawPassword password = new RawPassword("12345678");

        assertEquals("12345678", password.value());
    }

    @Test
    void rejectsPasswordShorterThanEightCharacters() {
        assertThrows(IllegalArgumentException.class, () -> new RawPassword("1234567"));
    }

    @Test
    void rejectsNullPassword() {
        assertThrows(IllegalArgumentException.class, () -> new RawPassword(null));
    }

    @Test
    void rejectsBlankPassword() {
        assertThrows(IllegalArgumentException.class, () -> new RawPassword("   "));
    }
}
