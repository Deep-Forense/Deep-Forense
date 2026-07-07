package com.deepforense.auth.domain.exception;

public class DuplicateEmailException extends RuntimeException {
    public DuplicateEmailException(String email) {
        super("Ya existe un usuario registrado con el email: " + email);
    }
}
