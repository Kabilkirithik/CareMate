import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/DashboardShell";
import { EmergencyAlert } from "@/components/dashboard/EmergencyAlert";
import { VoiceWave } from "@/components/dashboard/VoiceWave";
import { StaffAssignment } from "@/components/dashboard/StaffAssignment";
import { Mic, MicOff, Sparkles, User, Pill, FileText, Activity, ChevronDown, ChevronUp } from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { websocket } from "@/lib/websocket";

export const Route = createFileRoute("/doctor")({
  head: () => ({ meta: [{ title: "Doctor · CareMate" }] }),
  component: DoctorDashboard,
});

function DoctorDashboard() {
  const [queue, setQueue] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null);
  const [recording, setRecording] = useState(false);
  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [emergency, setEmergency] = useState<any>(null);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [patientSummary, setPatientSummary] = useState<any>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [showAssigned, setShowAssigned] = useState(false);

  const refreshQueue = async () => {
    try {
      const res = await api.getDoctorQueries();
      const formatted = res.queries.map((q: any) => ({
        id: q.interaction_id || q.request_id || q.patient_id + q.timestamp,
        patient: q.patient_id,
        room: q.room_id || q.room || "N/A",
        concern: q.message || q.transcript || q.request_text || "Patient query",
        urgency: q.intent === "emergency" ? "high" : "med",
        time: q.timestamp ? new Date(q.timestamp).toLocaleTimeString() : "Just now",
        intent: q.intent,
        patient_name: q.patient_name || `Patient ${q.patient_id?.slice(0, 8)}`,
      }));
      setQueue(formatted);
    } catch (e) {
      console.error("Queue fetch error:", e);
    }
  };

  const loadPatientSummary = async (patientId: string) => {
    setSummaryLoading(true);
    setPatientSummary(null);
    try {
      const [patientRes, vitalsRes, medsRes, notesRes] = await Promise.all([
        api.getPatientInfo(patientId).catch(() => null),
        api.getPatientVitals(patientId).catch(() => null),
        api.getPatientMedications(patientId).catch(() => null),
        api.getPatientNotes(patientId).catch(() => null),
      ]);
      setPatientSummary({
        patient: patientRes?.patient,
        vitals: vitalsRes?.vitals || [],
        medications: medsRes?.medications || [],
        notes: notesRes?.notes || [],
      });
    } catch (e) {
      console.error("Patient summary error:", e);
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleSelectQuery = (q: any) => {
    setActive(q);
    loadPatientSummary(q.patient);
    setRecordingBlob(null);
  };

  const sendVoiceReply = async () => {
    if (!active || !recordingBlob) { toast.error("Please record a message first."); return; }
    try {
      await api.sendDoctorVoiceResponse(active.patient, recordingBlob);
      toast.success("Voice reply delivered to patient device.");
      setRecordingBlob(null);
    } catch (e: any) {
      toast.error(e.message || "Failed to deliver voice reply");
    }
  };

  const toggleRecording = async () => {
    if (!recording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        const chunks: Blob[] = [];
        recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: "audio/wav" });
          if (blob.size < 1000) { toast.error("Recording too short."); return; }
          setRecordingBlob(blob);
          toast.success(`Recording ready (${Math.round(blob.size / 1024)}KB)`);
          stream.getTracks().forEach((t) => t.stop());
        };
        recorder.start();
        setMediaRecorder(recorder);
        setRecording(true);
        toast.info("Recording...");
      } catch {
        toast.error("Could not access microphone.");
      }
    } else {
      mediaRecorder?.stop();
      setRecording(false);
    }
  };

  // Auto-select first query on initial load
  useEffect(() => {
    if (queue.length > 0 && !active) {
      setActive(queue[0]);
      loadPatientSummary(queue[0].patient);
    }
  }, [queue]);

  useEffect(() => {
    refreshQueue();
    const pollInterval = setInterval(refreshQueue, 10000);
    
    // Connect WebSocket with staff credentials
    const user = api.getUser();
    if (user) {
      websocket.connect(undefined, user.id, user.role).catch(console.error);
    }
    
    websocket.on("message", (msg: any) => {
      const payload = msg.data ?? msg;
      if (msg.type === "EMERGENCY_ALERT") {
        setEmergency({ room: payload.room ?? payload.room_id, patient: payload.patient_id, reason: payload.message });
        toast.error("EMERGENCY DETECTED", { description: payload.message });
      }
      refreshQueue();
    });
    return () => {
      clearInterval(pollInterval);
      websocket.disconnect();
    };
  }, []);

  return (
    <DashboardShell role="doctor">
      {emergency && (
        <EmergencyAlert room={emergency.room} patient={`ID: ${emergency.patient.slice(0, 8)}`} reason={emergency.reason} />
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr_1fr]">
        {/* Left: Query Queue */}
        <section className="rounded-2xl border border-border bg-card p-4 shadow-soft">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Patient Query Queue</h2>
            <span className="rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold text-secondary">
              {queue.length} active
            </span>
          </div>
          <ul className="space-y-2 max-h-[60vh] overflow-y-auto">
            {queue.map((q) => (
              <li
                key={q.id}
                onClick={() => handleSelectQuery(q)}
                className={`cursor-pointer rounded-xl border p-3 transition ${
                  active?.id === q.id
                    ? "border-secondary bg-secondary/5"
                    : "border-border hover:border-secondary/40 hover:bg-muted"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${q.urgency === "high" ? "bg-destructive animate-pulse" : "bg-warning"}`} />
                  <p className="text-sm font-semibold truncate">{q.patient_name || `Patient ${q.patient.slice(0, 8)}`}</p>
                  <span className="ml-auto shrink-0 text-[10px] text-muted-foreground">{q.time}</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Room {q.room}</p>
                <p className="mt-1 line-clamp-1 text-xs">{q.concern}</p>
              </li>
            ))}
            {queue.length === 0 && (
              <p className="text-center text-xs text-muted-foreground py-10">No active queries</p>
            )}
          </ul>
        </section>

        {/* Centre: Voice Console */}
        <section className="rounded-2xl border border-border bg-gradient-card p-5 shadow-elevated">
          {active ? (
            <>
              <div>
                <p className="text-xs uppercase tracking-widest text-muted-foreground">Now responding</p>
                <h2 className="text-lg font-bold">Room {active.room} · {active.patient_name || active.patient.slice(0, 8)}</h2>
              </div>
              <div className="mt-4 rounded-2xl bg-muted/40 p-4">
                <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                  <Mic className="h-3.5 w-3.5 text-secondary" /> Patient Message
                </div>
                <VoiceWave bars={28} />
                <p className="mt-3 text-sm">"{active.concern}"</p>
              </div>
              <div className="mt-5 flex flex-col items-center">
                <button
                  onClick={toggleRecording}
                  className={`grid h-20 w-20 place-items-center rounded-full transition ${
                    recording
                      ? "bg-destructive text-destructive-foreground animate-emergency"
                      : "bg-primary text-primary-foreground shadow-glow hover:scale-105"
                  }`}
                >
                  {recording ? <MicOff className="h-7 w-7" /> : <Mic className="h-7 w-7" />}
                </button>
                <p className="mt-3 text-xs text-muted-foreground">
                  {recording
                    ? "Recording... tap to stop"
                    : recordingBlob
                    ? `Ready to send (${Math.round(recordingBlob.size / 1024)}KB)`
                    : "Tap & speak your reply"}
                </p>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-2">
                <button
                  onClick={sendVoiceReply}
                  disabled={!recordingBlob || recording}
                  className={`rounded-xl px-3 py-2.5 text-xs font-semibold transition ${
                    recordingBlob && !recording
                      ? "bg-success text-white shadow-glow hover:bg-success/90"
                      : "bg-muted text-muted-foreground cursor-not-allowed"
                  }`}
                >
                  {recordingBlob ? "Send Voice Note" : "Record first"}
                </button>
                <button
                  onClick={() => { setRecordingBlob(null); toast.info("Recording cleared"); }}
                  disabled={!recordingBlob}
                  className="rounded-xl border border-border bg-card px-3 py-2.5 text-xs font-semibold hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Clear
                </button>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
              Select a query from the queue to respond
            </div>
          )}
        </section>

        {/* Right: Patient Summary + Assigned Patients */}
        <div className="space-y-4">
          {/* Patient Summary */}
          <section className="rounded-2xl border border-border bg-card p-4 shadow-soft">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-secondary" />
              <h2 className="text-sm font-semibold">Patient Summary</h2>
            </div>

            {!active && (
              <p className="text-xs text-muted-foreground">Select a patient query to view their summary.</p>
            )}

            {active && summaryLoading && (
              <div className="space-y-2 animate-pulse">
                {[1, 2, 3, 4].map((i) => <div key={i} className="h-8 rounded-lg bg-muted" />)}
              </div>
            )}

            {active && !summaryLoading && patientSummary && (
              <div className="space-y-3 max-h-[50vh] overflow-y-auto">
                {/* Patient Info */}
                {patientSummary.patient && (
                  <div className="rounded-xl bg-muted/40 p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <User className="h-3.5 w-3.5 text-secondary" />
                      <span className="text-xs font-semibold">{patientSummary.patient.name}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1 text-[10px] text-muted-foreground">
                      <span>Age: {patientSummary.patient.age}</span>
                      <span>Blood: {patientSummary.patient.blood_group}</span>
                      {patientSummary.patient.allergies?.length > 0 && (
                        <span className="col-span-2 text-destructive font-medium">
                          ⚠ Allergies: {patientSummary.patient.allergies.join(", ")}
                        </span>
                      )}
                      {patientSummary.patient.chronic_conditions?.length > 0 && (
                        <span className="col-span-2">
                          Conditions: {patientSummary.patient.chronic_conditions.join(", ")}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Vitals */}
                {patientSummary.vitals?.length > 0 && (() => {
                  const v = patientSummary.vitals[0];
                  return (
                    <div className="rounded-xl bg-muted/40 p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <Activity className="h-3.5 w-3.5 text-success" />
                        <span className="text-xs font-semibold">Latest Vitals</span>
                      </div>
                      <div className="grid grid-cols-2 gap-1 text-[10px]">
                        {v?.blood_pressure && <span>BP: {v.blood_pressure}</span>}
                        {v?.heart_rate && <span>HR: {v.heart_rate} bpm</span>}
                        {v?.temperature && <span>Temp: {v.temperature}°F</span>}
                        {v?.oxygen_saturation && <span>SpO2: {v.oxygen_saturation}%</span>}
                      </div>
                    </div>
                  );
                })()}

                {/* Medications */}
                {patientSummary.medications?.length > 0 && (
                  <div className="rounded-xl bg-muted/40 p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <Pill className="h-3.5 w-3.5 text-warning" />
                      <span className="text-xs font-semibold">Medications</span>
                    </div>
                    <ul className="space-y-1">
                      {patientSummary.medications.slice(0, 3).map((m: any, i: number) => (
                        <li key={i} className="text-[10px] text-muted-foreground">
                          • {typeof m === "string" ? m : m.name} {m.dosage ? `— ${m.dosage}` : ""}
                        </li>
                      ))}
                      {patientSummary.medications.length > 3 && (
                        <li className="text-[10px] text-muted-foreground">
                          +{patientSummary.medications.length - 3} more
                        </li>
                      )}
                    </ul>
                  </div>
                )}

                {/* Notes */}
                {patientSummary.notes?.length > 0 && (
                  <div className="rounded-xl bg-muted/40 p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="h-3.5 w-3.5 text-secondary" />
                      <span className="text-xs font-semibold">Latest Note</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground line-clamp-4">
                      {patientSummary.notes[0]?.summary || patientSummary.notes[0]?.content || "No notes available"}
                    </p>
                  </div>
                )}

                {!patientSummary.patient &&
                  patientSummary.vitals?.length === 0 &&
                  patientSummary.medications?.length === 0 && (
                    <p className="text-xs text-muted-foreground">No records found for this patient.</p>
                  )}
              </div>
            )}
          </section>

          {/* Assigned Patients — collapsible */}
          <div>
            <button
              onClick={() => setShowAssigned((v) => !v)}
              className="flex w-full items-center justify-between rounded-xl border border-border bg-card px-4 py-2.5 text-xs font-semibold hover:bg-muted transition"
            >
              <span>My Assigned Patients</span>
              {showAssigned ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {showAssigned && <div className="mt-2"><StaffAssignment /></div>}
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
