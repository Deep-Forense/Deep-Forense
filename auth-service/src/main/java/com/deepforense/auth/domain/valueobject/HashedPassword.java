package com.deepforense.auth.domain.valueobject;

public final class HashedPassword {

    private final String hash;

    public HashedPassword(String hash) {
        if (hash == null || hash.isBlank()) {
            throw new IllegalArgumentException("El hash de password no puede estar vacío.");
        }
        this.hash = hash;
    }

    public String value() {
        return hash;
    }
}
