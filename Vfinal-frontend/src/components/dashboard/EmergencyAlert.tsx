import { AlertTriangle, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

interface Props {
  room: string;
  patient: string;
  reason: string;
}

export function EmergencyAlert({ room, patient, reason }: Props) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div className="animate-fade-up mb-4 overflow-hidden rounded-2xl border-2 border-destructive bg-destructive/5 shadow-emergency">
      <div className="flex items-center gap-3 bg-destructive px-4 py-3 text-destructive-foreground">
        <div className="grid h-9 w-9 animate-emergency place-items-center rounded-full bg-destructive-foreground/20">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-80">Code Red · Active Emergency</p>
          <p className="text-base font-bold leading-tight">
            Room {room} · {patient}
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="rounded-md p-1.5 transition hover:bg-destructive-foreground/15"
          aria-label="Acknowledge"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
        <p className="text-foreground">{reason}</p>
        <div className="flex gap-2">
          <button
            onClick={() => toast.success(`Responding to Room ${room}`, { description: "Team notified · ETA 90s" })}
            className="rounded-lg bg-destructive px-3 py-1.5 text-xs font-semibold text-destructive-foreground transition hover:opacity-90"
          >
            Respond Now
          </button>
          <button
            onClick={() => {
              toast("Emergency acknowledged", { description: `Room ${room} · ${patient}` });
              setDismissed(true);
            }}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold transition hover:bg-muted"
          >
            Acknowledge
          </button>
        </div>
      </div>
    </div>
  );
}
