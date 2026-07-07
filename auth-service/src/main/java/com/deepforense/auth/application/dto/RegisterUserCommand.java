package com.deepforense.auth.application.dto;

public record RegisterUserCommand(String email, String rawPassword) {}
