package com.deepforense.auth.application.dto;

public record LoginCommand(String email, String rawPassword) {}
