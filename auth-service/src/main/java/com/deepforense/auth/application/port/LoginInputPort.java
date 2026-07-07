package com.deepforense.auth.application.port;

import com.deepforense.auth.application.dto.AuthResult;
import com.deepforense.auth.application.dto.LoginCommand;

public interface LoginInputPort {
    AuthResult execute(LoginCommand command);
}
