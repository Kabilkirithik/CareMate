import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { User, Bed, Building2 } from "lucide-react";

interface AssignedPatient {
  patient_id: string;
  patient_name: string;
  room_id: string;
}

export function StaffAssignment() {
  const [assignment, setAssignment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [debugInfo, setDebugInfo] = useState<string>("");

  useEffect(() => {
    const loadAssignment = async () => {
      try {
        // Try caremate_user first (set after login fix)
        const stored = localStorage.getItem("caremate_user");
        
        if (stored) {
          const user = JSON.parse(stored);
          setDebugInfo(`User: ${user.name} (${user.id})`);
          const res = await api.getStaffAssignment(user.id);
          setAssignment(res.assignment);
          return;
        }

        // Fallback: use role from session + email from token to find staff
        const role = localStorage.getItem("caremate:role");
        const token = localStorage.getItem("caremate_token");
        
        setDebugInfo(`No user in storage. Role: ${role}, Token: ${token ? "present" : "missing"}`);
        
        if (role && token) {
          // Get staff directory and find by token (token contains staff_id prefix)
          // Token format: "token-XXXXXXXX" where XXXXXXXX is part of UUID
          // Try to get all staff of this role and show the first one's assignment
          // as a fallback until user re-logs in
          const staffRes = await api.getStaffDirectory(role === "nutrition" ? "nutritionist" : role);
          const staffList = staffRes.staff || [];
          
          if (staffList.length > 0) {
            // Use first staff member as demo fallback
            const firstStaff = staffList[0];
            const res = await api.getStaffAssignment(firstStaff.staff_id);
            setAssignment(res.assignment);
            setDebugInfo(`Fallback: showing ${firstStaff.name}'s assignment. Please re-login for your own data.`);
          }
        }
      } catch (e) {
        console.error("Failed to load assignment:", e);
        setDebugInfo(`Error: ${e}`);
      } finally {
        setLoading(false);
      }
    };
    loadAssignment();
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-4 shadow-soft animate-pulse">
        <div className="h-4 w-32 rounded bg-muted" />
        <div className="mt-3 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 rounded-xl bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (!assignment) {
    return (
      <section className="rounded-2xl border border-border bg-card p-4 shadow-soft">
        <div className="mb-2 flex items-center gap-2">
          <User className="h-4 w-4 text-secondary" />
          <h2 className="text-sm font-semibold">My Assigned Patients</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Please sign out and sign back in to load your assigned patients.
        </p>
        {debugInfo && (
          <p className="mt-1 text-[10px] text-muted-foreground/60">{debugInfo}</p>
        )}
      </section>
    );
  }

  const patients: AssignedPatient[] = assignment.assigned_patients || [];

  return (
    <section className="rounded-2xl border border-border bg-card p-4 shadow-soft">
      <div className="mb-3 flex items-center gap-2">
        <User className="h-4 w-4 text-secondary" />
        <h2 className="text-sm font-semibold">My Assigned Patients</h2>
        <span className="ml-auto rounded-full bg-secondary/10 px-2 py-0.5 text-[10px] font-semibold text-secondary">
          {patients.length} patients
        </span>
      </div>

      {debugInfo && !localStorage.getItem("caremate_user") && (
        <p className="mb-2 text-[10px] text-warning">
          ⚠ Re-login to see your own patients
        </p>
      )}

      {patients.length === 0 ? (
        <p className="text-center text-xs text-muted-foreground py-4">
          No patients assigned yet
        </p>
      ) : (
        <ul className="space-y-1.5 max-h-64 overflow-y-auto">
          {patients.map((p) => (
            <li
              key={p.patient_id}
              className="flex items-center gap-3 rounded-xl border border-border/60 bg-background px-3 py-2"
            >
              <div className="grid h-7 w-7 place-items-center rounded-lg bg-secondary/10 text-secondary">
                <User className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate">{p.patient_name}</p>
                <p className="text-[10px] text-muted-foreground">ID: {p.patient_id.slice(0, 8)}</p>
              </div>
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <Bed className="h-3 w-3" />
                <span>{p.room_id}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
