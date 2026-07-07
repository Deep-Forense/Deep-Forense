package com.deepforense.auth.domain.event;

import java.time.Instant;

public record UserRegistered(String userId, String email, Instant occurredAt) {

    public static UserRegistered now(String userId, String email) {
        return new UserRegistered(userId, email, Instant.now());
    }
}
