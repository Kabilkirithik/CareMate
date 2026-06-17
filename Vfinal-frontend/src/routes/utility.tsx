import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { Droplet, Plug, Sparkles, Bed, Armchair, Accessibility, CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";

export const Route = createFileRoute("/utility")({
  head: () => ({ meta: [{ title: "Utility · CareMate" }] }),
  component: UtilityDashboard,
});

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Water: Droplet,
  Charger: Plug,
  Housekeeping: Sparkles,
  Blanket: Bed,
  Cleaning: Sparkles,
  Wheelchair: Accessibility,
  general: Armchair,
};

interface Item {
  id: string;
  room: string;
  type: string;
  time: string;
  priority: "high" | "med" | "low";
  done?: boolean;
}

function mapPriority(p?: string): "high" | "med" | "low" {
  const u = (p || "").toUpperCase();
  if (u === "HIGH" || u === "CRITICAL") return "high";
  if (u === "MEDIUM" || u === "MED") return "med";
  return "low";
}

function UtilityDashboard() {
  const [items, setItems] = useState<Item[]>([]);
  const [queries, setQueries] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [maintenanceRes, utilityQueries] = await Promise.all([
          api.getMaintenanceRequests(),
          api.getUtilityQueries(),
        ]);
        
        // Set utility-specific queries
        setQueries(
          (utilityQueries.queries ?? []).map((q: any) => ({
            id: q.interaction_id || q.patient_id,
            room: q.room_id || q.room || "—",
            patient: q.patient_name || `Patient ${(q.patient_id || "").slice(0, 8)}`,
            request: q.message || q.transcript || "Utility request",
            intent: q.intent,
            time: q.timestamp ? new Date(q.timestamp).toLocaleTimeString() : "—",
          }))
        );
        
        const mapped = (maintenanceRes.requests ?? []).map((r: any) => ({
          id: r.request_id || r.interaction_id || String(Math.random()),
          room: r.room || r.room_id || "—",
          type: (r.category || r.request_text || "general").split(" ")[0],
          time: r.created_at ? new Date(r.created_at).toLocaleTimeString() : "—",
          priority: mapPriority(r.priority),
          done: r.status === "DONE",
        }));
        setItems(mapped);
      } catch (e) {
        console.error("Utility load error:", e);
      }
    };
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const toggle = async (id: string) => {
    // Optimistic update first
    setItems((s) =>
      s.map((i) => {
        if (i.id !== id) return i;
        const done = !i.done;
        if (done) toast.success(`Room ${i.room} · ${i.type} done`);
        else toast(`Room ${i.room} reopened`);
        return { ...i, done };
      })
    );
    // Persist to backend
    try {
      await api.resolveInteraction(id);
    } catch {
      // UI already updated, silent fail
    }
  };

  const addressQuery = async (q: any) => {
    try {
      await api.resolveInteraction(q.id);
    } catch {}
    setQueries((prev) => prev.filter((x) => x.id !== q.id));
    toast.success(`Request addressed`, { description: `Room ${q.room} · ${q.patient}` });
  };

  return (
    <DashboardShell role="utility">
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Open" value={items.filter((i) => !i.done).length.toString()} tint="text-warning" />
        <Stat label="High priority" value={items.filter((i) => i.priority === "high" && !i.done).length.toString()} tint="text-destructive" />
        <Stat label="Done today" value={items.filter((i) => i.done).length.toString()} tint="text-success" />
        <Stat label="Total queue" value={items.length.toString()} tint="text-secondary" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_2fr]">
        {/* Utility Queries */}
        <section className="rounded-2xl border border-border bg-card p-4 shadow-soft">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-secondary" />
            <h2 className="text-sm font-semibold">Patient Requests</h2>
            <span className="ml-auto rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold text-secondary">
              {queries.length} active
            </span>
          </div>
          <div className="space-y-2">
            {queries.length === 0 && (
              <p className="text-center text-xs text-muted-foreground py-4">No utility requests</p>
            )}
            {queries.map((q) => (
              <div key={q.id} className="rounded-xl border border-border/70 bg-background p-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-secondary" />
                  <p className="text-sm font-semibold">Room {q.room}</p>
                  <span className="ml-auto text-[10px] text-muted-foreground">{q.time}</span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">{q.patient}</p>
                <p className="mt-1 text-xs line-clamp-2">{q.request}</p>
                <button
                  onClick={() => addressQuery(q)}
                  className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg bg-secondary px-2 py-1.5 text-[11px] font-semibold text-secondary-foreground hover:bg-secondary/90 active:scale-95 transition"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" /> Mark Resolved
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Live Request Queue */}
        <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <h2 className="mb-4 text-sm font-semibold">Live request queue</h2>
          {items.length === 0 && <p className="text-sm text-muted-foreground">No open utility requests.</p>}
          <ul className="grid gap-2 sm:grid-cols-2">
            {items.map((i) => {
              const Icon = ICONS[i.type] || Armchair;
              return (
                <li
                  key={i.id}
                  className={`flex items-center gap-3 rounded-xl border p-3 transition ${
                    i.done ? "border-success/30 bg-success/5 opacity-70" : "border-border bg-background hover:border-secondary/40 hover:shadow-soft"
                  }`}
                >
                  <div className={`grid h-10 w-10 place-items-center rounded-xl ${i.done ? "bg-success/10 text-success" : "bg-secondary/10 text-secondary"}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold">Room {i.room}</p>
                      <span className={`h-1.5 w-1.5 rounded-full ${i.priority === "high" ? "bg-destructive" : i.priority === "med" ? "bg-warning" : "bg-success"}`} />
                      <span className="ml-auto text-[10px] text-muted-foreground">{i.time}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">{i.type}</p>
                  </div>
                  <button
                    onClick={() => toggle(i.id)}
                    className={`grid h-9 w-9 place-items-center rounded-lg transition ${
                      i.done ? "bg-success text-success-foreground" : "border border-border hover:bg-muted"
                    }`}
                    aria-label="Mark done"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </DashboardShell>
  );
}

function Stat({ label, value, tint }: { label: string; value: string; tint: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-3 text-center shadow-soft">
      <p className={`text-2xl font-black ${tint}`}>{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}
