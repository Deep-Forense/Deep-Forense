package com.deepforense.auth.domain.valueobject;

public final class RawPassword {

    private static final int MIN_LENGTH = 8;

    private final String value;

    public RawPassword(String value) {
        if (value == null || value.isBlank() || value.length() < MIN_LENGTH) {
            throw new IllegalArgumentException("La contraseña debe tener al menos 8 caracteres.");
        }
        this.value = value;
    }

    public String value() {
        return value;
    }
}
