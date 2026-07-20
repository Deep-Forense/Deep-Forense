package com.deepforense.auth.infrastructure.config;

import com.deepforense.auth.application.port.LoginInputPort;
import com.deepforense.auth.application.port.RegisterUserInputPort;
import com.deepforense.auth.application.usecase.LoginUseCase;
import com.deepforense.auth.application.usecase.RegisterUserUseCase;
import com.deepforense.auth.domain.port.PasswordHasherPort;
import com.deepforense.auth.domain.port.TokenProviderPort;
import com.deepforense.auth.domain.port.UserRepositoryPort;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;



@Configuration
public class UseCaseConfig {

    @Bean
    public RegisterUserInputPort registerUserUseCase(UserRepositoryPort repo, PasswordHasherPort hasher) {
        return new RegisterUserUseCase(repo, hasher);
    }

    @Bean
    public LoginInputPort loginUseCase(UserRepositoryPort repo, PasswordHasherPort hasher, TokenProviderPort tokenProvider) {
        return new LoginUseCase(repo, hasher, tokenProvider);
    }
}
