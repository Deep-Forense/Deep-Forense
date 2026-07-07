package com.deepforense.auth.infrastructure.adapter;

import com.deepforense.auth.domain.model.User;
import com.deepforense.auth.domain.port.UserRepositoryPort;
import com.deepforense.auth.domain.valueobject.Email;
import com.deepforense.auth.domain.valueobject.HashedPassword;
import org.springframework.stereotype.Component;

import java.util.Optional;

@Component
public class JpaUserRepositoryAdapter implements UserRepositoryPort {

    private final SpringDataUserJpaRepository jpaRepository;

    public JpaUserRepositoryAdapter(SpringDataUserJpaRepository jpaRepository) {
        this.jpaRepository = jpaRepository;
    }

    @Override
    public void save(User user) {
        UserJpaEntity entity = new UserJpaEntity(
                user.userId(), user.email().value(), user.password().value(), user.createdAt()
        );
        jpaRepository.save(entity);
    }

    @Override
    public Optional<User> findByEmail(Email email) {
        return jpaRepository.findByEmail(email.value())
                .map(e -> User.reconstitute(
                        e.getId(), new Email(e.getEmail()), new HashedPassword(e.getPasswordHash()), e.getCreatedAt()
                ));
    }

    @Override
    public boolean existsByEmail(Email email) {
        return jpaRepository.existsByEmail(email.value());
    }
}
