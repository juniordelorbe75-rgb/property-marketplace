export const LOGIN_WELCOME_KEY = "property_marketplace_login_welcome"
export const LOGIN_WELCOME_DURATION_MS = 15_000

export function queueLoginWelcome(kind = "returning", storage = sessionStorage) {
  storage.setItem(LOGIN_WELCOME_KEY, kind === "new" ? "new" : "returning")
}
