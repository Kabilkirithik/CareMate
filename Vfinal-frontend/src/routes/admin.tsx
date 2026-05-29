import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { OcrUpload } from "@/components/dashboard/OcrUpload";
import { Activity, Cpu, Database, ShieldAlert, Stethoscope, Users, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export const Route = createFileRoute("/admin")({
  head: () => ({ meta: [{ title: "Admin · CareMate" }] }),
  component: AdminDashboard,
});

function AdminDashboard() {
  const [metrics, setMetrics] = useState({
    total_patients: 0,
    active_visits: 0,
    emergency_alerts: 0,
    pending_requests: 0,
    staff_online: 0,
  });
  const [activities, setActivities] = useState<any[]>([]);
  const [emergencies, setEmergencies] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [health, setHealth] = useState({ status: "checking", database: "", agents: "" });

  useEffect(() => {
    const load = async () => {
      try {
        const [m, a, alerts, u, h] = await Promise.all([
          api.getSystemMetrics(),
          api.getUserActivities("24h"),
          api.getSystemAlerts(),
          api.getUsers(),
          api.healthCheck(),
        ]);
        const data = m.metrics ?? m;
        setMetrics({
          total_patients: data.total_patients ?? 0,
          active_visits: data.active_visits ?? 0,
          emergency_alerts: data.emergency_alerts ?? 0,
          pending_requests: data.pending_requests ?? 0,
          staff_online: data.staff_online ?? 0,
        });
        setActivities(a.activities ?? []);
        setEmergencies(alerts.alerts ?? []);
        setUsers(u.users ?? []);
        setHealth(h);
      } catch (e) {
        console.error("Admin dashboard load error:", e);
      }
    };
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  const activityCounts = activities.reduce<Record<string, number>>((acc, a) => {
    const key = a.intent || "other";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const chartData = Object.values(activityCounts).length
    ? Object.values(activityCounts)
    : [2, 4, 3, 6, 5, 8, 7];

  return (
    <DashboardShell role="admin">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KPI icon={<Users className="h-4 w-4" />} label="Active patients" value={String(metrics.total_patients)} delta={`${metrics.active_visits} visits`} />
        <KPI icon={<Stethoscope className="h-4 w-4" />} label="Staff accounts" value={String(metrics.staff_online)} delta="synced" tint="success" />
        <KPI icon={<Zap className="h-4 w-4" />} label="Pending requests" value={String(metrics.pending_requests)} delta="live" tint="success" />
        <KPI icon={<ShieldAlert className="h-4 w-4" />} label="Emergency alerts" value={String(metrics.emergency_alerts)} delta={metrics.emergency_alerts > 0 ? "active" : "clear"} tint={metrics.emergency_alerts > 0 ? "destructive" : "success"} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft lg:col-span-2">
          <h2 className="mb-4 text-sm font-semibold">Activity by intent (recent)</h2>
          <ChartBars data={chartData} />
          <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
            <Cell label="Interactions" value={String(activities.length)} tint="text-secondary" />
            <Cell label="Emergencies" value={String(metrics.emergency_alerts)} tint="text-destructive" />
            <Cell label="API" value={health.status} tint="text-success" />
          </div>
        </section>

        <section className="rounded-2xl border-2 border-destructive/30 bg-destructive/5 p-5 shadow-soft">
          <div className="mb-3 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-destructive" />
            <h2 className="text-sm font-semibold text-destructive">Active emergencies</h2>
          </div>
          <ul className="space-y-2">
            {emergencies.length === 0 && (
              <li className="rounded-xl border border-border bg-card p-3 text-xs text-muted-foreground">No active emergencies</li>
            )}
            {emergencies.map((e, i) => (
              <li key={i} className="rounded-xl border border-destructive/30 bg-card p-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-destructive" />
                  <p className="text-sm font-bold">Room {e.room}</p>
                </div>
                <p className="mt-1 text-xs">{e.message || e.type}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="mb-3 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-secondary" />
            <h2 className="text-sm font-semibold">AI monitoring</h2>
          </div>
          <div className="space-y-2">
            <Meter label="Agents" value={health.agents === "ready" ? 95 : 50} cap={100} />
            <Meter label="Database" value={health.database === "connected" ? 90 : 40} cap={100} tint="bg-success" />
            <Meter label="Interactions/hr" value={Math.min(activities.length * 5, 100)} cap={100} />
          </div>
        </section>

        <section className="lg:col-span-2">
          <OcrUpload />
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft lg:col-span-3">
          <div className="mb-3 flex items-center gap-2">
            <Activity className="h-4 w-4 text-secondary" />
            <h2 className="text-sm font-semibold">Staff directory</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-[11px] uppercase tracking-widest text-muted-foreground">
                <tr><th className="py-2">Name</th><th>Role</th><th>Email</th><th>ID</th></tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.slice(0, 12).map((row, i) => (
                  <tr key={i} className="text-xs">
                    <td className="py-2.5 font-semibold">{row.name}</td>
                    <td className="text-muted-foreground capitalize">{row.role}</td>
                    <td>{row.email}</td>
                    <td className="text-muted-foreground">{row.staff_id?.slice?.(0, 8) ?? row.staff_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft lg:col-span-3">
          <div className="mb-3 flex items-center gap-2">
            <Database className="h-4 w-4 text-secondary" />
            <h2 className="text-sm font-semibold">Infrastructure</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
            <Cell label="MongoDB" value={health.database || "—"} tint="text-success" />
            <Cell label="FastAPI" value={health.status || "—"} tint="text-success" />
            <Cell label="ChromaDB" value="Ready" tint="text-success" />
            <Cell label="Agents" value={health.agents || "—"} tint="text-secondary" />
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}

function KPI({ icon, label, value, delta, tint }: { icon: React.ReactNode; label: string; value: string; delta: string; tint?: "success" | "destructive" }) {
  const dt = tint === "destructive" ? "text-destructive" : tint === "success" ? "text-success" : "text-muted-foreground";
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
      <div className="flex items-center gap-2 text-muted-foreground">
        <span className="grid h-7 w-7 place-items-center rounded-md bg-muted">{icon}</span>
        <p className="text-xs">{label}</p>
      </div>
      <p className="mt-2 text-2xl font-black">{value}</p>
      <p className={`text-[11px] font-semibold ${dt}`}>{delta}</p>
    </div>
  );
}

function Cell({ label, value, tint }: { label: string; value: string; tint: string }) {
  return (
    <div className="rounded-xl border border-border bg-background p-3">
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className={`mt-1 text-sm font-bold ${tint}`}>{value}</p>
    </div>
  );
}

function Meter({ label, value, cap, tint = "bg-secondary" }: { label: string; value: number; cap: number; tint?: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold">{value}</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-muted">
        <div className={`h-full rounded-full ${tint}`} style={{ width: `${(value / cap) * 100}%` }} />
      </div>
    </div>
  );
}

function ChartBars({ data }: { data: number[] }) {
  const max = Math.max(...data, 1);
  return (
    <div className="flex h-32 items-end gap-1">
      {data.map((d, i) => (
        <div
          key={i}
          className="flex-1 rounded-t-md bg-gradient-to-t from-secondary/40 to-secondary transition hover:from-secondary hover:to-accent"
          style={{ height: `${(d / max) * 100}%` }}
          title={`${d} reqs`}
        />
      ))}
    </div>
  );
}
