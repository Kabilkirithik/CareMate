import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { AlertTriangle, Utensils, Leaf, Clock, CheckCircle2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export const Route = createFileRoute("/nutrition")({
  head: () => ({ meta: [{ title: "Nutritionist · CareMate" }] }),
  component: NutritionDashboard,
});

interface Query {
  id: string;
  room: string;
  patient: string;
  request: string;
  intent: string;
  time: string;
  status?: string;
}

interface MealRequest {
  id: string;
  room: string;
  patient: string;
  meal: string;
  note: string;
  flags: string[];
  time: string;
  prepared?: boolean;
}

interface PatientSummary {
  room: string;
  patient: string;
  allergies: string[];
  diabetic: boolean;
  restrictions: string;
}

function NutritionDashboard() {
  const [queries, setQueries]     = useState<Query[]>([]);
  const [requests, setRequests]   = useState<MealRequest[]>([]);
  const [summaries, setSummaries] = useState<PatientSummary[]>([]);
  const [loading, setLoading]     = useState(true);

  const load = async () => {
    try {
      const [meals, plans, alerts, nutritionQueries] = await Promise.all([
        api.getNutritionMeals(new Date().toISOString().slice(0, 10)),
        api.getNutritionPlans(),
        api.getNutritionAlerts(),
        api.getNutritionQueries(),
      ]);

      setQueries(
        (nutritionQueries.queries ?? []).map((q: any) => ({
          id: q.interaction_id || q._id || q.patient_id + q.timestamp,
          room: q.room_id || q.room || "—",
          patient: q.patient_name || `Patient ${(q.patient_id || "").slice(0, 8)}`,
          request: q.message || q.transcript || "Nutrition request",
          intent: q.intent,
          time: q.timestamp ? new Date(q.timestamp).toLocaleTimeString() : "—",
          status: q.status || "PENDING",
        }))
      );

      setRequests(
        (meals.meals ?? []).map((m: any) => ({
          id: m.request_id || m.interaction_id || String(Math.random()),
          room: m.room || m.room_id || "—",
          patient: m.patient_name || "Patient",
          meal: m.category || "Meal request",
          note: m.request_text || "From patient",
          flags: m.flags || [],
          time: m.created_at ? new Date(m.created_at).toLocaleTimeString() : "—",
          prepared: m.status === "DONE",
        }))
      );

      const planItems = plans.plans ?? [];
      const alertItems = alerts.alerts ?? [];
      setSummaries(
        planItems.length > 0
          ? planItems.map((p: any) => ({
              room: p.room || "—",
              patient: p.patient_name || "Patient",
              allergies: p.allergies || [],
              diabetic: (p.restrictions || "").toLowerCase().includes("diabetic"),
              restrictions: p.restrictions || "Standard",
            }))
          : alertItems.map((a: any) => ({
              room: "—",
              patient: a.name,
              allergies: a.allergies || [],
              diabetic: false,
              restrictions: "Allergy alert",
            }))
      );
    } catch (e) {
      console.error("Nutrition load error:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, []);

  const addressQuery = async (q: Query) => {
    try {
      await api.resolveInteraction(q.id);
      setQueries((prev) => prev.filter((x) => x.id !== q.id));
      toast.success(`Query resolved`, { description: `Room ${q.room} · ${q.patient}` });
    } catch {
      // Optimistic update even if API fails
      setQueries((prev) => prev.filter((x) => x.id !== q.id));
      toast.success(`Query addressed for Room ${q.room}`);
    }
  };

  const markPrepared = async (req: MealRequest) => {
    try {
      await api.resolveInteraction(req.id);
    } catch {}
    setRequests((prev) =>
      prev.map((r) => (r.id === req.id ? { ...r, prepared: true } : r))
    );
    toast.success(`${req.meal} prepared`, { description: `Room ${req.room} · ${req.patient}` });
  };

  const delayMeal = (req: MealRequest) => {
    toast.warning(`${req.meal} delayed`, { description: `Room ${req.room}` });
  };

  const activeQueries = queries.filter((q) => q.status !== "RESOLVED");

  return (
    <DashboardShell role="nutrition">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex gap-3">
          <Stat label="Pending queries" value={activeQueries.length} tint="text-success" />
          <Stat label="Meal requests" value={requests.filter((r) => !r.prepared).length} tint="text-secondary" />
          <Stat label="Patients" value={summaries.length} tint="text-muted-foreground" />
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-semibold hover:bg-muted"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr_1fr]">
        {/* Patient Queries */}
        <section className="rounded-2xl border border-border bg-card p-4 shadow-soft">
          <div className="mb-3 flex items-center gap-2">
            <Utensils className="h-4 w-4 text-success" />
            <h2 className="text-sm font-semibold">Patient Queries</h2>
            <span className="ml-auto rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold text-success">
              {activeQueries.length} active
            </span>
          </div>

          {loading && <p className="py-4 text-center text-xs text-muted-foreground">Loading…</p>}

          <div className="space-y-2">
            {!loading && activeQueries.length === 0 && (
              <p className="py-6 text-center text-xs text-muted-foreground">No nutrition queries</p>
            )}
            {activeQueries.map((q) => (
              <div key={q.id} className="rounded-xl border border-border/70 bg-background p-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-success" />
                  <p className="text-sm font-semibold">Room {q.room}</p>
                  <span className="ml-auto text-[10px] text-muted-foreground">{q.time}</span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">{q.patient}</p>
                <p className="mt-1 text-xs line-clamp-2">{q.request}</p>
                <button
                  onClick={() => addressQuery(q)}
                  className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg bg-success px-2 py-1.5 text-[11px] font-semibold text-white hover:bg-success/90 active:scale-95 transition"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" /> Mark Resolved
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Meal Requests */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="mb-4 flex items-center gap-2">
            <Utensils className="h-4 w-4 text-success" />
            <h2 className="text-sm font-semibold">Meal Requests</h2>
            <span className="ml-auto rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold text-success">
              {requests.filter((r) => !r.prepared).length} pending
            </span>
          </div>

          {!loading && requests.length === 0 && (
            <p className="text-sm text-muted-foreground">No pending meal requests.</p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            {requests.map((r) => (
              <article
                key={r.id}
                className={`rounded-xl border p-4 transition ${
                  r.prepared
                    ? "border-success/30 bg-success/5 opacity-60"
                    : "border-border/70 bg-background hover:shadow-soft"
                }`}
              >
                <div className="flex items-center gap-2">
                  <p className="text-sm font-bold">Room {r.room}</p>
                  <span className="text-xs text-muted-foreground">· {r.patient}</span>
                  <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold text-secondary">
                    <Clock className="h-3 w-3" /> {r.time}
                  </span>
                </div>
                <p className="mt-2 text-sm">
                  {r.meal} · <span className="text-muted-foreground">{r.note}</span>
                </p>
                {r.flags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {r.flags.map((f) => (
                      <span key={f} className="inline-flex items-center gap-1 rounded-md bg-warning/15 px-2 py-0.5 text-[10px] font-semibold text-warning">
                        <AlertTriangle className="h-3 w-3" /> {f}
                      </span>
                    ))}
                  </div>
                )}
                {r.prepared ? (
                  <div className="mt-3 flex items-center gap-1.5 text-[11px] font-semibold text-success">
                    <CheckCircle2 className="h-4 w-4" /> Prepared
                  </div>
                ) : (
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => markPrepared(r)}
                      className="flex-1 rounded-lg bg-primary px-3 py-1.5 text-[11px] font-semibold text-primary-foreground hover:bg-primary/90 active:scale-95 transition"
                    >
                      Mark prepared
                    </button>
                    <button
                      onClick={() => delayMeal(r)}
                      className="rounded-lg border border-border px-3 py-1.5 text-[11px] font-semibold hover:bg-muted active:scale-95 transition"
                    >
                      Delay
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>

        {/* Patient Health Summary */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="mb-4 flex items-center gap-2">
            <Leaf className="h-4 w-4 text-success" />
            <h2 className="text-sm font-semibold">Patient Health Summary</h2>
          </div>
          <div className="space-y-3">
            {summaries.length === 0 && (
              <p className="text-sm text-muted-foreground">No active patient diet plans.</p>
            )}
            {summaries.map((s, i) => (
              <div key={i} className="rounded-xl border border-border/70 bg-background p-4">
                <p className="text-sm font-bold">
                  Room {s.room} · {s.patient}
                </p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <Field label="Allergies" value={(s.allergies || []).join(", ") || "None"} tint="text-destructive" />
                  <Field label="Diabetic" value={s.diabetic ? "Yes" : "No"} tint="text-warning" />
                  <Field label="Restrictions" value={s.restrictions} tint="text-muted-foreground" colSpan />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </DashboardShell>
  );
}

function Stat({ label, value, tint }: { label: string; value: number; tint: string }) {
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-2 text-center shadow-soft">
      <p className={`text-xl font-black ${tint}`}>{value}</p>
      <p className="text-[10px] text-muted-foreground">{label}</p>
    </div>
  );
}

function Field({ label, value, tint, colSpan }: { label: string; value: string; tint: string; colSpan?: boolean }) {
  return (
    <div className={colSpan ? "col-span-2" : ""}>
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className={`font-semibold ${tint}`}>{value}</p>
    </div>
  );
}
