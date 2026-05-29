import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { AlertTriangle, Utensils, Leaf, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export const Route = createFileRoute("/nutrition")({
  head: () => ({ meta: [{ title: "Nutritionist · CareMate" }] }),
  component: NutritionDashboard,
});

function NutritionDashboard() {
  const [requests, setRequests] = useState<any[]>([]);
  const [summaries, setSummaries] = useState<any[]>([]);
  const [queries, setQueries] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [meals, plans, alerts, nutritionQueries] = await Promise.all([
          api.getNutritionMeals(new Date().toISOString().slice(0, 10)),
          api.getNutritionPlans(),
          api.getNutritionAlerts(),
          api.getNutritionQueries(),
        ]);
        
        // Set nutrition-specific queries
        setQueries(
          (nutritionQueries.queries ?? []).map((q: any) => ({
            id: q.interaction_id || q.patient_id,
            room: q.room_id || q.room || "—",
            patient: q.patient_name || `Patient ${(q.patient_id || "").slice(0, 8)}`,
            request: q.message || q.transcript || "Nutrition request",
            intent: q.intent,
            time: q.timestamp ? new Date(q.timestamp).toLocaleTimeString() : "—",
          }))
        );
        
        setRequests(
          (meals.meals ?? []).map((m: any) => ({
            room: m.room || m.room_id || "—",
            patient: m.patient_name || "Patient",
            meal: m.category || "Meal request",
            note: m.request_text || "From patient",
            flags: [],
            time: m.created_at ? new Date(m.created_at).toLocaleTimeString() : "—",
          }))
        );
        const planItems = plans.plans ?? [];
        const alertItems = alerts.alerts ?? [];
        const summaryList =
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
              }));
        setSummaries(summaryList);
      } catch (e) {
        console.error("Nutrition load error:", e);
      }
    };
    load();
  }, []);

  return (
    <DashboardShell role="nutrition">
      <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr_1fr]">
        {/* Nutrition Queries */}
        <section className="rounded-2xl border border-border bg-card p-4 shadow-soft">
          <div className="mb-3 flex items-center gap-2">
            <Utensils className="h-4 w-4 text-success" />
            <h2 className="text-sm font-semibold">Patient Queries</h2>
            <span className="ml-auto rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold text-success">
              {queries.length} active
            </span>
          </div>
          <div className="space-y-2">
            {queries.length === 0 && (
              <p className="text-center text-xs text-muted-foreground py-4">No nutrition queries</p>
            )}
            {queries.map((q) => (
              <div key={q.id} className="rounded-xl border border-border/70 bg-background p-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-success" />
                  <p className="text-sm font-semibold">Room {q.room}</p>
                  <span className="ml-auto text-[10px] text-muted-foreground">{q.time}</span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">{q.patient}</p>
                <p className="mt-1 text-xs line-clamp-2">{q.request}</p>
                <button
                  onClick={() => toast.success(`Nutrition query addressed for Room ${q.room}`)}
                  className="mt-2 w-full rounded-lg bg-success px-2 py-1.5 text-[11px] font-semibold text-success-foreground hover:bg-success/90"
                >
                  Address Query
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
              {requests.length} live
            </span>
          </div>
          {requests.length === 0 && (
            <p className="text-sm text-muted-foreground">No pending nutrition requests.</p>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            {requests.map((r, i) => (
              <article key={i} className="rounded-xl border border-border/70 bg-background p-4 transition hover:shadow-soft">
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
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {r.flags.map((f: string) => (
                    <span key={f} className="inline-flex items-center gap-1 rounded-md bg-warning/15 px-2 py-0.5 text-[10px] font-semibold text-warning">
                      <AlertTriangle className="h-3 w-3" /> {f}
                    </span>
                  ))}
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => toast.success(`${r.meal} prepared`, { description: `Room ${r.room} · ${r.patient}` })}
                    className="flex-1 rounded-lg bg-primary px-3 py-1.5 text-[11px] font-semibold text-primary-foreground hover:bg-primary/90"
                  >
                    Mark prepared
                  </button>
                  <button
                    onClick={() => toast.warning(`${r.meal} delayed`, { description: `Room ${r.room}` })}
                    className="rounded-lg border border-border px-3 py-1.5 text-[11px] font-semibold hover:bg-muted"
                  >
                    Delay
                  </button>
                </div>
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

function Field({ label, value, tint, colSpan }: { label: string; value: string; tint: string; colSpan?: boolean }) {
  return (
    <div className={colSpan ? "col-span-2" : ""}>
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className={`font-semibold ${tint}`}>{value}</p>
    </div>
  );
}
