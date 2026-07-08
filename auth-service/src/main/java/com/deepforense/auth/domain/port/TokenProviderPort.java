package com.deepforense.auth.domain.port;

public interface TokenProviderPort {
    /** Genera un JWT firmado con el subject = userId y un claim "email". */
    String generateToken(String userId, String email);

    /** Devuelve el email (subject de negocio) contenido en el token, o vacío si es inválido/expiró. */
    java.util.Optional<String> extractEmail(String token);
}
