package com.deepforense.auth.domain.port;

import com.deepforense.auth.domain.model.User;
import com.deepforense.auth.domain.valueobject.Email;

import java.util.Optional;

public interface UserRepositoryPort {
    void save(User user);
    Optional<User> findByEmail(Email email);
    boolean existsByEmail(Email email);
}
