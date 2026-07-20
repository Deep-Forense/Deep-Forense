package com.deepforense.auth.infrastructure.entrypoint.rest;

import com.deepforense.auth.application.dto.AuthResult;
import com.deepforense.auth.application.dto.LoginCommand;
import com.deepforense.auth.application.dto.RegisterUserCommand;
import com.deepforense.auth.application.port.LoginInputPort;
import com.deepforense.auth.application.port.RegisterUserInputPort;
import com.deepforense.auth.domain.exception.DuplicateEmailException;
import com.deepforense.auth.domain.exception.InvalidCredentialsException;
import com.deepforense.auth.domain.model.User;
import com.deepforense.auth.domain.port.UserRepositoryPort;
import com.deepforense.auth.domain.valueobject.Email;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final RegisterUserInputPort registerUserUseCase;
    private final LoginInputPort loginUseCase;
    private final UserRepositoryPort userRepository;

    public AuthController(RegisterUserInputPort registerUserUseCase, LoginInputPort loginUseCase,
                           UserRepositoryPort userRepository) {
        this.registerUserUseCase = registerUserUseCase;
        this.loginUseCase = loginUseCase;
        this.userRepository = userRepository;
    }

    public record RegisterRequest(String name, String email, String password) {}
    public record LoginRequest(String email, String password) {}

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody RegisterRequest request) {
        try {
            String userId = registerUserUseCase.execute(
                    new RegisterUserCommand(request.name(), request.email(), request.password())
            );
            return ResponseEntity.status(201).body(Map.of("id", userId, "name", request.name(), "email", request.email()));
        } catch (DuplicateEmailException e) {
            return ResponseEntity.status(409).body(Map.of("error_code", "EMAIL_ALREADY_REGISTERED", "message", e.getMessage()));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error_code", "INVALID_REGISTRATION_DATA", "message", e.getMessage()));
        }
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request) {
        try {
            AuthResult result = loginUseCase.execute(new LoginCommand(request.email(), request.password()));
            return ResponseEntity.ok(Map.of(
                    "access_token", result.accessToken(),
                    "token_type", result.tokenType(),
                    "expires_in", result.expiresIn(),
                    "user", Map.of("id", result.userId(), "email", result.email())
            ));
        } catch (InvalidCredentialsException e) {
            return ResponseEntity.status(401).body(Map.of("error_code", "INVALID_CREDENTIALS", "message", e.getMessage()));
        }
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout() {

        return ResponseEntity.noContent().build();
    }

    @GetMapping("/me")
    public ResponseEntity<?> me(Authentication authentication) {
        if (authentication == null) {
            return ResponseEntity.status(401).body(Map.of("error_code", "UNAUTHENTICATED", "message", "Token inválido o ausente."));
        }

        String email = (String) authentication.getPrincipal();
        return userRepository.findByEmail(new Email(email))
                .map(this::toUserResponse)
                .orElseGet(() -> ResponseEntity.status(401).body(Map.of("error_code", "UNAUTHENTICATED", "message", "Usuario no encontrado.")));
    }

    private ResponseEntity<?> toUserResponse(User user) {
        return ResponseEntity.ok(Map.of(
                "id", user.userId(),
                "name", user.name(),
                "email", user.email().value(),
                "created_at", user.createdAt().toString()
        ));
    }
}
