export type UserRole = "owner" | "worker";

export interface SessionUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  company_id: string | null;
}

export interface AppSession {
  accessToken: string;
  user: SessionUser;
}

const SESSION_KEY = "nexushub_session";
const SESSION_CHANGED_EVENT = "nexushub-session-changed";

function emitSessionChanged(): void {
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

export function getSession(): AppSession | null {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AppSession;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function setSession(session: AppSession): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  emitSessionChanged();
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
  emitSessionChanged();
}

export function onSessionChanged(listener: () => void): () => void {
  const handler = () => listener();
  window.addEventListener(SESSION_CHANGED_EVENT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(SESSION_CHANGED_EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}
