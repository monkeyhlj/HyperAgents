import { reactive } from "vue";

const TOKEN_KEY = "ha_token";
const USER_KEY = "ha_user";

const savedToken = localStorage.getItem(TOKEN_KEY) || "";
const savedUserText = localStorage.getItem(USER_KEY);

export const authState = reactive({
  token: savedToken,
  user: savedUserText ? JSON.parse(savedUserText) : null
});

export function isAuthenticated() {
  return !!authState.token;
}

export function saveAuth(session) {
  authState.token = session.access_token;
  authState.user = session.user;
  localStorage.setItem(TOKEN_KEY, authState.token);
  localStorage.setItem(USER_KEY, JSON.stringify(authState.user));
}

export function clearAuth() {
  authState.token = "";
  authState.user = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
