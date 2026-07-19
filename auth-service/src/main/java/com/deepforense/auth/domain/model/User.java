package com.deepforense.auth.domain.model;

import com.deepforense.auth.domain.event.UserRegistered;
import com.deepforense.auth.domain.valueobject.Email;
import com.deepforense.auth.domain.valueobject.HashedPassword;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class User {

    private final String userId;
    private final String name;
    private final Email email;
    private final HashedPassword password;
    private final Instant createdAt;
    private final List<Object> domainEvents = new ArrayList<>();

    private User(String userId, String name, Email email, HashedPassword password, Instant createdAt) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("El nombre no puede estar vacío.");
        }
        this.userId = userId;
        this.name = name;
        this.email = email;
        this.password = password;
        this.createdAt = createdAt;
    }

    /** Factory: única forma de crear un User nuevo (emite UserRegistered). */
    public static User register(String name, Email email, HashedPassword password) {
        User user = new User(UUID.randomUUID().toString(), name, email, password, Instant.now());
        user.domainEvents.add(UserRegistered.now(user.userId, email.value()));
        return user;
    }

    /** Reconstrucción desde persistencia: no emite eventos de dominio. */
    public static User reconstitute(String userId, String name, Email email, HashedPassword password, Instant createdAt) {
        return new User(userId, name, email, password, createdAt);
    }

    public String userId() { return userId; }
    public String name() { return name; }
    public Email email() { return email; }
    public HashedPassword password() { return password; }
    public Instant createdAt() { return createdAt; }

    public List<Object> pullDomainEvents() {
        List<Object> events = new ArrayList<>(domainEvents);
        domainEvents.clear();
        return events;
    }
}
