package com.deepforense.auth.application.dto;

public record RegisterUserCommand(String name, String email, String rawPassword) {}
