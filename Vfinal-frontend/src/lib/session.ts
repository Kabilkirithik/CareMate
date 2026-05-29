import type { Role } from "./roles";

const KEY = "caremate:role";

export function getRole(): Role | null {
  if (typeof window === "undefined") return null;
  return (localStorage.getItem(KEY) as Role | null) ?? null;
}

export function setRole(role: Role) {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, role);
}

export function clearRole() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(KEY);
}
