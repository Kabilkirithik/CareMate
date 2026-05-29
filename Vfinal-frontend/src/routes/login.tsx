import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Activity, ArrowRight, Lock } from "lucide-react";
import { useState } from "react";
import { ROLES, type Role } from "@/lib/roles";
import { setRole as saveRole } from "@/lib/session";
import { api } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/login")({
  head: () => ({ meta: [{ title: "Sign in · CareMate" }] }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [role, setRole] = useState<Role>("doctor");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("hospital123");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.login(email, password);
      api.setToken(res.token);
      // Store full user object so dashboards can filter by staff_id
      localStorage.setItem('caremate_user', JSON.stringify(res.user));
      saveRole(res.user.role as Role);
      toast.success(`Welcome back, ${res.user.name}`);
      const path = ROLES.find((r) => r.id === res.user.role)!.path;
      navigate({ to: path });
    } catch (e: any) {
      toast.error("Login Failed", { description: "Invalid email or password." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="absolute inset-0 -z-10 bg-gradient-aurora" />
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6">
        <Link to="/" className="flex items-center gap-2 self-start">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-hero text-primary-foreground shadow-glow">
            <Activity className="h-4 w-4" />
          </div>
          <span className="font-bold tracking-tight">CareMate</span>
        </Link>

        <div className="flex flex-1 items-center justify-center py-10">
          <div className="grid w-full max-w-4xl gap-6 md:grid-cols-[1.1fr_1fr]">
            <div className="hidden flex-col justify-between rounded-3xl bg-gradient-hero p-8 text-primary-foreground shadow-elevated md:flex">
              <div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-foreground/15 px-2.5 py-1 text-xs font-medium">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-success" /> Live coordination
                </span>
                <h2 className="mt-6 text-3xl font-bold leading-tight">
                  Sign in to the hospital portal.
                </h2>
                <p className="mt-3 text-primary-foreground/80">
                  One sign-in, the right dashboard. Voice-first, real-time, mobile-friendly.
                </p>
              </div>
              <ul className="space-y-2 text-sm text-primary-foreground/80">
                <li>· Role-based access & routing</li>
                <li>· Emergency-grade alert delivery</li>
                <li>· Works on low networks · PWA</li>
              </ul>
            </div>

            <form
              onSubmit={submit}
              className="animate-fade-up rounded-3xl border border-border bg-card p-7 shadow-elevated"
            >
              <h1 className="text-2xl font-bold">Welcome back</h1>
              <p className="mt-1 text-sm text-muted-foreground">Pick your role to continue.</p>

              <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {ROLES.map((r) => (
                  <button
                    type="button"
                    key={r.id}
                    onClick={() => setRole(r.id)}
                    className={`rounded-xl border p-3 text-left text-xs transition ${
                      role === r.id
                        ? "border-primary bg-primary/5 shadow-soft"
                        : "border-border hover:border-secondary/50 hover:bg-muted"
                    }`}
                  >
                    <p className="font-semibold">{r.label}</p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">{r.tagline}</p>
                  </button>
                ))}
              </div>

              <div className="mt-5 space-y-3">
                <label className="block">
                  <span className="text-xs font-medium text-muted-foreground">Email</span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="staff@hospital.org"
                    className="mt-1 w-full rounded-xl border border-input bg-background px-3 py-2.5 text-sm outline-none transition focus:border-secondary focus:ring-2 focus:ring-ring/30"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-muted-foreground">Password</span>
                  <div className="relative mt-1">
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full rounded-xl border border-input bg-background px-3 py-2.5 pr-9 text-sm outline-none transition focus:border-secondary focus:ring-2 focus:ring-ring/30"
                    />
                    <Lock className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  </div>
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-glow transition hover:bg-primary/90 ${loading ? "opacity-70" : ""}`}
              >
                {loading ? "Signing in..." : "Sign in to dashboard"} <ArrowRight className="h-4 w-4" />
              </button>

              <p className="mt-3 text-center text-[11px] text-muted-foreground">
                Credentials synced from hospital staff directory.
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
