package com.deepforense.auth.application.usecase;

import com.deepforense.auth.application.dto.RegisterUserCommand;
import com.deepforense.auth.application.port.RegisterUserInputPort;
import com.deepforense.auth.domain.exception.DuplicateEmailException;
import com.deepforense.auth.domain.model.User;
import com.deepforense.auth.domain.port.PasswordHasherPort;
import com.deepforense.auth.domain.port.UserRepositoryPort;
import com.deepforense.auth.domain.valueobject.Email;
import com.deepforense.auth.domain.valueobject.HashedPassword;

/** No lleva @Service: se instancia en infrastructure/config (composition root). */
public class RegisterUserUseCase implements RegisterUserInputPort {

    private final UserRepositoryPort userRepository;
    private final PasswordHasherPort passwordHasher;

    public RegisterUserUseCase(UserRepositoryPort userRepository, PasswordHasherPort passwordHasher) {
        this.userRepository = userRepository;
        this.passwordHasher = passwordHasher;
    }

    @Override
    public String execute(RegisterUserCommand command) {
        Email email = new Email(command.email());

        if (userRepository.existsByEmail(email)) {
            throw new DuplicateEmailException(email.value());
        }

        HashedPassword hashedPassword = passwordHasher.hash(command.rawPassword());
        User user = User.register(email, hashedPassword);

        userRepository.save(user);

        // En producción: publicar user.pullDomainEvents() a un event bus.

        return user.userId();
    }
}
