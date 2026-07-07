package com.deepforense.auth.application.usecase;

import com.deepforense.auth.application.dto.AuthResult;
import com.deepforense.auth.application.dto.LoginCommand;
import com.deepforense.auth.application.port.LoginInputPort;
import com.deepforense.auth.domain.exception.InvalidCredentialsException;
import com.deepforense.auth.domain.model.User;
import com.deepforense.auth.domain.port.PasswordHasherPort;
import com.deepforense.auth.domain.port.TokenProviderPort;
import com.deepforense.auth.domain.port.UserRepositoryPort;
import com.deepforense.auth.domain.valueobject.Email;

/** No lleva @Service: se instancia en infrastructure/config (composition root). */
public class LoginUseCase implements LoginInputPort {

    private static final long EXPIRES_IN_SECONDS = 3600;

    private final UserRepositoryPort userRepository;
    private final PasswordHasherPort passwordHasher;
    private final TokenProviderPort tokenProvider;

    public LoginUseCase(UserRepositoryPort userRepository, PasswordHasherPort passwordHasher,
                         TokenProviderPort tokenProvider) {
        this.userRepository = userRepository;
        this.passwordHasher = passwordHasher;
        this.tokenProvider = tokenProvider;
    }

    @Override
    public AuthResult execute(LoginCommand command) {
        Email email = new Email(command.email());

        User user = userRepository.findByEmail(email)
                .orElseThrow(InvalidCredentialsException::new);

        if (!passwordHasher.matches(command.rawPassword(), user.password())) {
            throw new InvalidCredentialsException();
        }

        String token = tokenProvider.generateToken(user.userId(), user.email().value());

        return new AuthResult(token, "Bearer", EXPIRES_IN_SECONDS, user.userId(), user.email().value());
    }
}
