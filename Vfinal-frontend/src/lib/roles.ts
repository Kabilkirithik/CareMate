export type Role = "doctor" | "nurse" | "nutrition" | "utility" | "admin";

export interface RoleMeta {
  id: Role;
  label: string;
  tagline: string;
  path: string;
  accent: string; // tailwind text color class
}

export const ROLES: RoleMeta[] = [
  { id: "doctor", label: "Doctor", tagline: "Voice-first patient queue", path: "/doctor", accent: "text-secondary" },
  { id: "nurse", label: "Nurse", tagline: "Live request workflow", path: "/nurse", accent: "text-accent-foreground" },
  { id: "nutrition", label: "Nutritionist", tagline: "Diet & meal coordination", path: "/nutrition", accent: "text-success" },
  { id: "utility", label: "Utility Staff", tagline: "Facility requests", path: "/utility", accent: "text-warning" },
  { id: "admin", label: "Admin", tagline: "Hospital command center", path: "/admin", accent: "text-primary" },
];
