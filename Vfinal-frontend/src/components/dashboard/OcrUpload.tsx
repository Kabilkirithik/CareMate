import { FileText, ScanLine, Upload, CheckCircle2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface UploadedReport {
  id: string;
  name: string;
  size: string;
  patient: string;
  status: "processing" | "indexed";
}

export function OcrUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [reports, setReports] = useState<UploadedReport[]>([]);
  const [drag, setDrag] = useState(false);
  const [defaultPatientId, setDefaultPatientId] = useState<string | null>(null);

  useEffect(() => {
    api.getNurseAssignments().then((res) => {
      const first = res.assignments?.[0]?.patient_id;
      if (first) setDefaultPatientId(first);
    }).catch(() => {});
  }, []);

  const handleFiles = async (files: FileList | null) => {
    if (!files) return;
    
    for (const file of Array.from(files)) {
      const id = `n${Date.now()}`;
      const newReport: UploadedReport = {
        id,
        name: file.name,
        size: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
        patient: "Assigning...",
        status: "processing",
      };
      
      setReports((r) => [newReport, ...r]);

      try {
        const patientId = defaultPatientId;
        if (!patientId) {
          toast.error("No active patient assignment found. Seed the database first.");
          setReports((r) => r.filter((x) => x.id !== id));
          continue;
        }
        await api.uploadDocument(patientId, file);
        toast.success(`Report ${file.name} uploaded and indexed.`);
        setReports((r) => r.map((x) => (x.id === id ? { ...x, status: "indexed", patient: "Linked to Room" } : x)));
      } catch (e) {
        toast.error(`Failed to upload ${file.name}`);
        setReports((r) => r.filter((x) => x.id !== id));
      }
    }
  };

  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
      <div className="mb-4 flex items-center gap-2">
        <ScanLine className="h-4 w-4 text-secondary" />
        <h3 className="font-semibold">OCR Report Upload</h3>
        <span className="ml-auto text-xs text-muted-foreground">PDF · JPG · PNG</span>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`group flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition ${
          drag ? "border-secondary bg-secondary/5" : "border-border hover:border-secondary/50 hover:bg-muted/40"
        }`}
      >
        <div className="grid h-10 w-10 place-items-center rounded-full bg-secondary/10 text-secondary transition group-hover:scale-110">
          <Upload className="h-5 w-5" />
        </div>
        <p className="text-sm font-medium">Drop reports to OCR & index</p>
        <p className="text-xs text-muted-foreground">Auto-processed by ChromaDB · linked to patient room</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,image/*"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <ul className="mt-4 space-y-2">
        {reports.map((r) => (
          <li
            key={r.id}
            className="flex items-center gap-3 rounded-lg border border-border/70 bg-background p-2.5"
          >
            <div className="grid h-8 w-8 place-items-center rounded-md bg-muted">
              <FileText className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{r.name}</p>
              <p className="text-xs text-muted-foreground">
                {r.patient} · {r.size}
              </p>
            </div>
            {r.status === "processing" ? (
              <span className="flex items-center gap-1.5 rounded-full bg-warning/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-warning">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-warning" /> OCR
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded-full bg-success/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-success">
                <CheckCircle2 className="h-3 w-3" /> Indexed
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
