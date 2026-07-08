package com.deepforense.auth.domain.port;

import com.deepforense.auth.domain.valueobject.HashedPassword;

public interface PasswordHasherPort {
    HashedPassword hash(String rawPassword);
    boolean matches(String rawPassword, HashedPassword hashedPassword);
}
