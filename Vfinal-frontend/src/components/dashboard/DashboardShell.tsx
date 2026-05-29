import { Link, useNavigate } from "@tanstack/react-router";
import { Activity, Bell, LogOut, Wifi } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ROLES, type Role } from "@/lib/roles";
import { clearRole, getRole } from "@/lib/session";
import { api } from "@/lib/api";

interface Props {
  role: Role;
  children: React.ReactNode;
}

const NOTIFICATIONS: Record<Role, { title: string; body: string; time: string }[]> = {
  doctor: [
    { title: "New patient query", body: "A. Sharma · Room 204 · chest pain", time: "2m" },
    { title: "Lab report indexed", body: "Blood panel ready for Room 312", time: "14m" },
    { title: "Shift handover at 18:00", body: "Pending notes for 3 patients", time: "1h" },
  ],
  nurse: [
    { title: "IV assistance requested", body: "Room 204 · high priority", time: "1m" },
    { title: "Bandage check due", body: "Room 118 · M. Khan", time: "4m" },
    { title: "Code blue resolved", body: "Room 412 stable", time: "22m" },
  ],
  nutrition: [
    { title: "New meal request", body: "Room 204 · low-sodium lunch", time: "5m" },
    { title: "Allergy flag updated", body: "R. Iyer · shellfish added", time: "30m" },
  ],
  utility: [
    { title: "Wheelchair requested", body: "Room 210 · high priority", time: "10m" },
    { title: "Housekeeping pending", body: "Room 312", time: "16m" },
  ],
  admin: [
    { title: "SLA breach", body: "Room 208 response > 5m", time: "3m" },
    { title: "ChromaDB reindex started", body: "ETA 4 minutes", time: "6m" },
    { title: "Doctor offline", body: "Dr. Karan signed off", time: "20m" },
  ],
};

export function DashboardShell({ role, children }: Props) {
  const meta = ROLES.find((r) => r.id === role)!;
  const navigate = useNavigate();
  const [openNotif, setOpenNotif] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  // Enforce that the logged-in role matches the route
  useEffect(() => {
    const current = getRole();
    if (!current) {
      navigate({ to: "/login" });
      return;
    }
    if (current !== role) {
      const target = ROLES.find((r) => r.id === current);
      if (target) navigate({ to: target.path });
    }
  }, [role, navigate]);

  // Close notif dropdown on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setOpenNotif(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      api.clearToken();
    }
    clearRole();
    toast.success("Signed out");
    navigate({ to: "/" });
  };

  const notifications = NOTIFICATIONS[role];

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-3 px-4 md:px-6">
          <Link to="/" className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-hero text-primary-foreground shadow-glow">
              <Activity className="h-4 w-4" />
            </div>
            <span className="font-bold tracking-tight">CareMate</span>
          </Link>
          <span className="hidden text-muted-foreground md:inline">/</span>
          <span className="hidden text-sm font-medium md:inline">{meta.label} Dashboard</span>

          <div className="ml-auto flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-1 text-xs font-medium text-success sm:inline-flex">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-success" /> Live
            </span>
            <button
              onClick={() => toast("Network status: stable", { description: "Connection 98% · low-bandwidth mode ready" })}
              className="grid h-9 w-9 place-items-center rounded-lg text-muted-foreground transition hover:bg-muted hover:text-foreground"
              aria-label="Network"
            >
              <Wifi className="h-4 w-4" />
            </button>

            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setOpenNotif((v) => !v)}
                className="relative grid h-9 w-9 place-items-center rounded-lg text-muted-foreground transition hover:bg-muted hover:text-foreground"
                aria-label="Notifications"
              >
                <Bell className="h-4 w-4" />
                {notifications.length > 0 && (
                  <span className="absolute right-1.5 top-1.5 grid h-4 w-4 place-items-center rounded-full bg-destructive text-[9px] font-bold text-destructive-foreground">
                    {notifications.length}
                  </span>
                )}
              </button>
              {openNotif && (
                <div className="absolute right-0 mt-2 w-80 overflow-hidden rounded-xl border border-border bg-card shadow-elevated">
                  <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
                    <p className="text-sm font-semibold">Notifications</p>
                    <button
                      onClick={() => {
                        setOpenNotif(false);
                        toast.success("All notifications marked as read");
                      }}
                      className="text-[11px] font-medium text-secondary hover:underline"
                    >
                      Mark all read
                    </button>
                  </div>
                  <ul className="max-h-80 overflow-y-auto">
                    {notifications.map((n, i) => (
                      <li key={i} className="border-b border-border/60 px-4 py-3 last:border-0 hover:bg-muted/50">
                        <div className="flex items-start gap-2">
                          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" />
                          <div className="flex-1">
                            <p className="text-sm font-medium">{n.title}</p>
                            <p className="text-xs text-muted-foreground">{n.body}</p>
                          </div>
                          <span className="text-[10px] text-muted-foreground">{n.time}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <button
              onClick={handleLogout}
              className="grid h-9 w-9 place-items-center rounded-lg text-muted-foreground transition hover:bg-muted hover:text-foreground"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Single role badge — only the logged-in dashboard is reachable */}
        <div className="mx-auto flex max-w-[1600px] items-center gap-2 px-4 pb-2 md:px-6">
          <span className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground">
            {meta.label}
          </span>
          <span className="text-xs text-muted-foreground">{meta.tagline}</span>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-6 md:px-6">{children}</main>
    </div>
  );
}
