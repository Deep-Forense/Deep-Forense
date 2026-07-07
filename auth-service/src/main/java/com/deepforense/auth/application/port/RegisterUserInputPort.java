package com.deepforense.auth.application.port;

import com.deepforense.auth.application.dto.RegisterUserCommand;

public interface RegisterUserInputPort {
    String execute(RegisterUserCommand command);
}
