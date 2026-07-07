package com.deepforense.auth.infrastructure.adapter;

import com.deepforense.auth.domain.port.PasswordHasherPort;
import com.deepforense.auth.domain.valueobject.HashedPassword;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

@Component
public class BCryptPasswordHasherAdapter implements PasswordHasherPort {

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    @Override
    public HashedPassword hash(String rawPassword) {
        return new HashedPassword(encoder.encode(rawPassword));
    }

    @Override
    public boolean matches(String rawPassword, HashedPassword hashedPassword) {
        return encoder.matches(rawPassword, hashedPassword.value());
    }
}
