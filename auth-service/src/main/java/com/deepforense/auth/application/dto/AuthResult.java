package com.deepforense.auth.application.dto;

public record AuthResult(String accessToken, String tokenType, long expiresIn, String userId, String email) {}
