package com.deepforense.auth.domain.port;

public interface TokenProviderPort {

    String generateToken(String userId, String email);


    java.util.Optional<String> extractEmail(String token);
}
