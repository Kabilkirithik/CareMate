import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { OcrUpload } from "@/components/dashboard/OcrUpload";
import {
  Activity, Cpu, Database, ShieldAlert, Stethoscope,
  Users, Zap, RefreshCw, CheckCircle2, Clock,
} from "lucide-react";
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
  const [loading, setLoading] = useState(true);

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
        total_patients:   data.total_patients   ?? 0,
        active_visits:    data.active_visits    ?? 0,
        emergency_alerts: data.emergency_alerts ?? 0,
        pending_requests: data.pending_requests ?? 0,
        staff_online:     data.staff_online     ?? 0,
      });
      setActivities(a.activities ?? []);
      setEmergencies(alerts.alerts ?? []);
      setUsers(u.users ?? []);
      setHealth(h);
    } catch (e) {
      console.error("Admin load error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  // Group activities by intent for chart
  const intentGroups = activities.reduce<Record<string, number>>((acc, a) => {
    const key = a.intent || "other";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const chartEntries = Object.entries(intentGroups).sort((a, b) => b[1] - a[1]);
  const chartValues = chartEntries.length ? chartEntries.map(([, v]) => v) : [0];

  return (
    <DashboardShell role="admin">
      {/* ── KPI Row ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <KPI icon={<Users className="h-4 w-4" />}        label="Patients"          value={metrics.total_patients}   delta={`${metrics.active_visits} active`} />
        <KPI icon={<Stethoscope className="h-4 w-4" />}  label="Staff accounts"    value={metrics.staff_online}     delta="total"   tint="success" />
        <KPI icon={<Zap className="h-4 w-4" />}          label="Interactions"      value={activities.length}        delta="last 24h" tint="success" />
        <KPI icon={<Clock className="h-4 w-4" />}        label="Pending requests"  value={metrics.pending_requests} delta="open"    tint="warning" />
        <KPI icon={<ShieldAlert className="h-4 w-4" />}  label="Emergencies"       value={metrics.emergency_alerts} delta={metrics.emergency_alerts > 0 ? "active" : "clear"} tint={metrics.emergency_alerts > 0 ? "destructive" : "success"} />
      </div>

      {/* ── Row 2: Chart + Emergencies + AI Status ──────────────── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* Activity chart */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft lg:col-span-2">
          <div className="mb-1 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Activity by intent (last 24h)</h2>
            <button onClick={load} className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted">
              <RefreshCw className="h-3 w-3" /> Refresh
            </button>
          </div>
          <ChartBars data={chartValues} labels={chartEntries.map(([k]) => k)} />
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4 text-xs">
            {chartEntries.slice(0, 4).map(([key, count]) => (
              <Cell key={key} label={key.replace("_", " ")} value={String(count)} tint="text-secondary" />
            ))}
          </div>
        </section>

        {/* Emergencies */}
        <section className="rounded-2xl border-2 border-destructive/30 bg-destructive/5 p-5 shadow-soft">
          <div className="mb-3 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-destructive" />
            <h2 className="text-sm font-semibold text-destructive">Emergency alerts</h2>
            <span className="ml-auto rounded-full bg-destructive/15 px-2 py-0.5 text-[10px] font-bold text-destructive">
              {emergencies.length}
            </span>
          </div>
          <ul className="space-y-2 max-h-64 overflow-y-auto">
            {emergencies.length === 0 ? (
              <li className="flex items-center gap-2 rounded-xl border border-border bg-card p-3 text-xs text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 text-success" /> No active emergencies
              </li>
            ) : (
              emergencies.map((e, i) => (
                <li key={i} className="rounded-xl border border-destructive/30 bg-card p-3">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-destructive" />
                    <p className="text-sm font-bold">Room {e.room || "—"}</p>
                    <span className="ml-auto text-[10px] text-muted-foreground">
                      {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : ""}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                    {e.message || e.type || "Emergency alert"}
                  </p>
                </li>
              ))
            )}
          </ul>
        </section>
      </div>

      {/* ── Row 3: AI Status + OCR ───────────────────────────────── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="mb-3 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-secondary" />
            <h2 className="text-sm font-semibold">System status</h2>
            <span className={`ml-auto h-2 w-2 rounded-full ${health.status === "online" ? "bg-success animate-pulse" : "bg-muted-foreground"}`} />
          </div>
          <div className="space-y-3">
            <Meter label="FastAPI" value={health.status === "online" ? 100 : 0} cap={100} tint="bg-success" status={health.status} />
            <Meter label="Database" value={health.database === "connected" ? 100 : 0} cap={100} tint="bg-success" status={health.database} />
            <Meter label="Agents" value={health.agents === "ready" ? 100 : 50} cap={100} status={health.agents} />
            <Meter label="Activity load" value={Math.min(activities.length * 3, 100)} cap={100} tint="bg-secondary" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <Cell label="ChromaDB" value="Ready" tint="text-success" />
            <Cell label="WebSocket" value="Active" tint="text-success" />
          </div>
        </section>

        <section className="lg:col-span-2">
          <OcrUpload />
        </section>
      </div>

      {/* ── Row 4: Staff Directory ───────────────────────────────── */}
      <div className="mt-4 rounded-2xl border border-border bg-card p-5 shadow-soft">
        <div className="mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4 text-secondary" />
          <h2 className="text-sm font-semibold">Staff directory</h2>
          <span className="ml-auto text-xs text-muted-foreground">{users.length} accounts</span>
        </div>
        {loading ? (
          <p className="py-4 text-center text-xs text-muted-foreground">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-widest text-muted-foreground">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Role</th>
                  <th className="pb-2 pr-4">Department</th>
                  <th className="pb-2 pr-4">Email</th>
                  <th className="pb-2">Shift</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {users.slice(0, 15).map((row, i) => (
                  <tr key={i} className="text-xs hover:bg-muted/30 transition">
                    <td className="py-2.5 pr-4 font-semibold">{row.name}</td>
                    <td className="pr-4">
                      <RoleBadge role={row.role} />
                    </td>
                    <td className="pr-4 text-muted-foreground">{row.department || "—"}</td>
                    <td className="pr-4 text-muted-foreground">{row.email}</td>
                    <td className="text-muted-foreground">{row.shift || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Row 5: Recent Activity ───────────────────────────────── */}
      <div className="mt-4 rounded-2xl border border-border bg-card p-5 shadow-soft">
        <div className="mb-3 flex items-center gap-2">
          <Database className="h-4 w-4 text-secondary" />
          <h2 className="text-sm font-semibold">Recent interactions</h2>
          <span className="ml-auto text-xs text-muted-foreground">{activities.length} in last 24h</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-widest text-muted-foreground">
                <th className="pb-2 pr-4">Patient</th>
                <th className="pb-2 pr-4">Intent</th>
                <th className="pb-2 pr-4">Message</th>
                <th className="pb-2">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {activities.slice(0, 10).map((a, i) => (
                <tr key={i} className="hover:bg-muted/30 transition">
                  <td className="py-2 pr-4 font-semibold">{a.patient_name || a.patient_id || "—"}</td>
                  <td className="pr-4">
                    <IntentBadge intent={a.intent} />
                  </td>
                  <td className="pr-4 max-w-xs truncate text-muted-foreground">
                    {a.message || a.transcript || "—"}
                  </td>
                  <td className="text-muted-foreground whitespace-nowrap">
                    {a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : "—"}
                  </td>
                </tr>
              ))}
              {activities.length === 0 && (
                <tr><td colSpan={4} className="py-4 text-center text-muted-foreground">No recent activity</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardShell>
  );
}

// ── Sub-components ───────────────────────────────────────────────────────────

function KPI({
  icon, label, value, delta, tint,
}: {
  icon: React.ReactNode; label: string; value: number; delta: string;
  tint?: "success" | "destructive" | "warning";
}) {
  const dt =
    tint === "destructive" ? "text-destructive" :
    tint === "warning"     ? "text-warning" :
    tint === "success"     ? "text-success" :
    "text-muted-foreground";
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-soft">
      <div className="flex items-center gap-2 text-muted-foreground">
        <span className="grid h-7 w-7 place-items-center rounded-md bg-muted">{icon}</span>
        <p className="text-xs leading-tight">{label}</p>
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

function Meter({
  label, value, cap, tint = "bg-secondary", status,
}: {
  label: string; value: number; cap: number; tint?: string; status?: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold capitalize text-[11px]">{status || value}</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-muted">
        <div className={`h-full rounded-full transition-all ${tint}`} style={{ width: `${(value / cap) * 100}%` }} />
      </div>
    </div>
  );
}

function ChartBars({ data, labels }: { data: number[]; labels?: string[] }) {
  const max = Math.max(...data, 1);
  return (
    <div className="flex h-28 items-end gap-1 mt-3">
      {data.map((d, i) => (
        <div key={i} className="group relative flex-1">
          <div
            className="w-full rounded-t-sm bg-gradient-to-t from-secondary/40 to-secondary transition hover:from-secondary hover:to-accent"
            style={{ height: `${(d / max) * 100}%` }}
          />
          {labels?.[i] && (
            <div className="absolute bottom-[-18px] left-0 right-0 overflow-hidden text-center text-[9px] text-muted-foreground truncate px-0.5">
              {labels[i].replace("_request", "").replace("_query", "")}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function RoleBadge({ role }: { role: string }) {
  const colours: Record<string, string> = {
    doctor:       "bg-blue-100 text-blue-700",
    nurse:        "bg-cyan-100 text-cyan-700",
    nutrition:    "bg-green-100 text-green-700",
    nutritionist: "bg-green-100 text-green-700",
    utility:      "bg-orange-100 text-orange-700",
    admin:        "bg-purple-100 text-purple-700",
  };
  const cls = colours[role?.toLowerCase()] || "bg-muted text-muted-foreground";
  return (
    <span className={`rounded-md px-2 py-0.5 text-[10px] font-semibold capitalize ${cls}`}>
      {role}
    </span>
  );
}

function IntentBadge({ intent }: { intent: string }) {
  const colours: Record<string, string> = {
    emergency:         "bg-red-100 text-red-700",
    doctor_query:      "bg-blue-100 text-blue-700",
    nurse_request:     "bg-cyan-100 text-cyan-700",
    nutrition_request: "bg-green-100 text-green-700",
    utility_request:   "bg-orange-100 text-orange-700",
    status_query:      "bg-yellow-100 text-yellow-700",
    general_conversation: "bg-muted text-muted-foreground",
  };
  const cls = colours[intent] || "bg-muted text-muted-foreground";
  return (
    <span className={`rounded-md px-2 py-0.5 text-[10px] font-semibold ${cls}`}>
      {(intent || "—").replace("_", " ")}
    </span>
  );
}
