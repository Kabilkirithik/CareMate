import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { EmergencyAlert } from "@/components/dashboard/EmergencyAlert";
import { OcrUpload } from "@/components/dashboard/OcrUpload";
import { CheckCircle2, Clock, AlertTriangle, Play } from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { websocket } from "@/lib/websocket";

export const Route = createFileRoute("/nurse")({
  head: () => ({ meta: [{ title: "Nurse · CareMate" }] }),
  component: NurseDashboard,
});

/** Generates a repeating alarm beep using the Web Audio API — no external file needed */
function playAlarm(times = 4) {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    let offset = 0;
    for (let i = 0; i < times; i++) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "square";
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.6, ctx.currentTime + offset);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + offset + 0.3);
      osc.start(ctx.currentTime + offset);
      osc.stop(ctx.currentTime + offset + 0.35);
      offset += 0.45;
    }
  } catch {
    // AudioContext not available — silently skip
  }
}

type Status = "new" | "in_progress" | "done";
interface Req {
  id: string;
  room: string;
  patient: string;
  type: string;
  priority: "high" | "med" | "low";
  time: string;
  status: Status;
}

function NurseDashboard() {
  const [reqs, setReqs] = useState<Req[]>([]);
  const [emergency, setEmergency] = useState<any>(null);

  const refreshNurseQueue = async () => {
    try {
      // Use the new nurse-specific queries endpoint
      const nurseRes = await api.getNurseQueries();
      
      const formatted = nurseRes.queries.map((r: any) => ({
        id: r.interaction_id || r.patient_id + (r.timestamp ?? ""),
        room: r.room_id || r.room || "N/A",
        patient: r.patient_name || `Patient ${(r.patient_id || "").slice(0, 8)}`,
        type: r.message || r.transcript || "Nurse Request",
        priority: r.intent === "emergency" ? "high" : "med",
        time: r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : "Now",
        status: "new" as Status,
      }));
      
      setReqs(formatted);
    } catch (e) {
      console.error("Nurse queue error:", e);
      // Fallback to general activities if nurse endpoint fails
      try {
        const activityRes = await api.getUserActivities("1h");
        const nurseRequests = activityRes.activities.filter((a: any) =>
          ["nurse_request", "medication_query", "vital_signs"].includes(a.intent)
        );

        const formatted = nurseRequests.map((r: any) => ({
          id: r.interaction_id || r.patient_id + (r.timestamp ?? ""),
          room: r.room_id || r.room || "N/A",
          patient: r.patient_name || `Patient ${(r.patient_id || "").slice(0, 8)}`,
          type: r.message || r.transcript || "Nurse Request",
          priority: r.intent === "emergency" ? "high" : "med",
          time: r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : "Now",
          status: "new" as Status,
        }));
        setReqs(formatted);
      } catch (fallbackError) {
        console.error("Fallback nurse queue error:", fallbackError);
      }
    }
  };

  useEffect(() => {
    refreshNurseQueue();
    
    // Connect WebSocket with staff credentials
    const user = api.getUser();
    if (user) {
      websocket.connect(undefined, user.id, user.role).catch(console.error);
    }
    
    websocket.on("message", (msg: any) => {
      const payload = msg.data ?? msg;
      if (msg.type === "EMERGENCY_ALERT") {
        setEmergency({
          room: payload.room ?? payload.room_id,
          patient: payload.patient_id,
          reason: payload.message,
        });
        // 🚨 Play alarm sound
        playAlarm();
      }
      refreshNurseQueue();
    });
    
    return () => {
      websocket.disconnect();
    };
  }, []);

  const set = (id: string, status: Status) => setReqs((r) => r.map((x) => (x.id === id ? { ...x, status } : x)));

  const groups: { key: Status; label: string; tint: string }[] = [
    { key: "new", label: "New", tint: "text-destructive" },
    { key: "in_progress", label: "In Progress", tint: "text-warning" },
    { key: "done", label: "Completed", tint: "text-success" },
  ];

  return (
    <DashboardShell role="nurse">
      {emergency && (
        <EmergencyAlert 
          room={emergency.room} 
          patient={`ID: ${emergency.patient.slice(0,8)}`} 
          reason={emergency.reason} 
        />
      )}

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="grid gap-4 sm:grid-cols-3">
          {groups.map((g) => (
            <section key={g.key} className="rounded-2xl border border-border bg-card p-4 shadow-soft">
              <div className="mb-3 flex items-center justify-between">
                <h2 className={`text-sm font-semibold ${g.tint}`}>{g.label}</h2>
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                  {reqs.filter((r) => r.status === g.key).length}
                </span>
              </div>
              <ul className="space-y-2">
                {reqs.filter((r) => r.status === g.key).map((r) => (
                  <li key={r.id} className="rounded-xl border border-border/70 bg-background p-3">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${r.priority === "high" ? "bg-destructive" : r.priority === "med" ? "bg-warning" : "bg-success"}`} />
                      <p className="text-sm font-semibold">Room {r.room}</p>
                      <span className="ml-auto text-[10px] text-muted-foreground">{r.time}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">{r.patient}</p>
                    <p className="mt-1 text-sm">{r.type}</p>
                    <div className="mt-3 flex gap-1.5">
                      {r.status === "new" && (
                        <button onClick={() => { set(r.id, "in_progress"); toast.success(`Accepted Room ${r.room}`); }} className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg bg-primary px-2 py-1.5 text-[11px] font-semibold text-primary-foreground hover:bg-primary/90">
                          <Play className="h-3 w-3" /> Accept
                        </button>
                      )}
                      {r.status === "in_progress" && (
                        <button onClick={() => { set(r.id, "done"); toast.success(`Room ${r.room} completed`); }} className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg bg-success px-2 py-1.5 text-[11px] font-semibold text-success-foreground hover:opacity-90">
                          <CheckCircle2 className="h-3 w-3" /> Complete
                        </button>
                      )}
                    </div>
                  </li>
                ))}
                {reqs.filter((r) => r.status === g.key).length === 0 && (
                  <li className="rounded-xl border border-dashed border-border p-4 text-center text-xs text-muted-foreground">
                    All clear
                  </li>
                )}
              </ul>
            </section>
          ))}
        </div>

        <div className="space-y-4">
          <OcrUpload />
        </div>
      </div>
    </DashboardShell>
  );
}

function Stat({ label, value, tint }: { label: string; value: string; tint: string }) {
  return (
    <div className="rounded-xl border border-border bg-background p-3 text-center">
      <p className={`text-2xl font-black ${tint}`}>{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}
