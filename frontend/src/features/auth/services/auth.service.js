import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from "@/api/client";

const TOKEN_KEY = "deepforense_token";
const USER_KEY = "deepforense_user";

export async function login(credentials) {
  const { data } = await loginRequest(credentials);
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  return data;
}

export async function registerAndLogin(payload) {
  await registerRequest(payload);
  return login({ email: payload.email, password: payload.password });
}

export async function logout() {
  try {
    await logoutRequest();
  } finally {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

export async function fetchCurrentUser() {
  const { data } = await getCurrentUser();
  return data;
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem(TOKEN_KEY));
}
