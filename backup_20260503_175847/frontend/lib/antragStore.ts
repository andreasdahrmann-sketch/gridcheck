// lib/antragStore.ts
// Storage-Layer fuer Antrags-Metadaten (Status, Notiz, Audit-Log)
// Revisionssicher light: append-only Audit mit Hash-Kette

export type AntragStatus =
  | "eingegangen"
  | "in_pruefung"
  | "rueckfrage"
  | "genehmigt"
  | "abgelehnt";

export const STATUS_LABEL: Record<AntragStatus, string> = {
  eingegangen: "Eingegangen",
  in_pruefung: "In Prüfung",
  rueckfrage: "Rückfrage",
  genehmigt: "Genehmigt",
  abgelehnt: "Abgelehnt",
};

export const STATUS_COLOR: Record<AntragStatus, string> = {
  eingegangen: "bg-slate-500",
  in_pruefung: "bg-blue-500",
  rueckfrage: "bg-amber-500",
  genehmigt: "bg-emerald-500",
  abgelehnt: "bg-rose-500",
};

export type AuditAction =
  | "created"
  | "status_changed"
  | "note_added"
  | "note_updated";

export interface AuditEntry {
  id: string;             // uuid
  antrag_id: string;
  timestamp: string;      // ISO-8601 UTC
  action: AuditAction;
  user: string;           // Platzhalter, spaeter echter User
  old_value: string | null;
  new_value: string | null;
  comment: string | null;
  prev_hash: string;      // Hash des vorherigen Eintrags (Kette)
  hash: string;           // Hash dieses Eintrags
}

export interface AntragMeta {
  antrag_id: string;
  status: AntragStatus;
  note: string;
  updated_at: string;     // ISO-8601 UTC
}

const STORAGE_KEY_META = "gridcheck_antrag_meta";
const STORAGE_KEY_AUDIT = "gridcheck_antrag_audit";

// ---------- Hash (einfacher djb2, fuer Kette ausreichend) ----------
function simpleHash(input: string): string {
  let hash = 5381;
  for (let i = 0; i < input.length; i++) {
    hash = ((hash << 5) + hash) + input.charCodeAt(i);
    hash = hash & 0xffffffff;
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "id-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// ---------- Meta lesen/schreiben ----------
function readAllMeta(): Record<string, AntragMeta> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY_META);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeAllMeta(data: Record<string, AntragMeta>): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY_META, JSON.stringify(data));
}

export function getMeta(antrag_id: string): AntragMeta {
  const all = readAllMeta();
  return (
    all[antrag_id] ?? {
      antrag_id,
      status: "eingegangen",
      note: "",
      updated_at: new Date().toISOString(),
    }
  );
}

// ---------- Audit lesen/schreiben (append-only) ----------
function readAllAudit(): AuditEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY_AUDIT);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeAllAudit(data: AuditEntry[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY_AUDIT, JSON.stringify(data));
}

export function getAuditTrail(antrag_id: string): AuditEntry[] {
  return readAllAudit()
    .filter((e) => e.antrag_id === antrag_id)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function appendAudit(
  antrag_id: string,
  action: AuditAction,
  old_value: string | null,
  new_value: string | null,
  comment: string | null,
  user: string = "system"
): AuditEntry {
  const all = readAllAudit();
  const trail = all
    .filter((e) => e.antrag_id === antrag_id)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  const prev_hash = trail.length > 0 ? trail[trail.length - 1].hash : "0".repeat(8);

  const entry: Omit<AuditEntry, "hash"> = {
    id: uuid(),
    antrag_id,
    timestamp: new Date().toISOString(),
    action,
    user,
    old_value,
    new_value,
    comment,
    prev_hash,
  };
  const hash = simpleHash(JSON.stringify(entry));
  const full: AuditEntry = { ...entry, hash };
  all.push(full);
  writeAllAudit(all);
  return full;
}

// ---------- Public API ----------
export function setStatus(
  antrag_id: string,
  newStatus: AntragStatus,
  comment: string = "",
  user: string = "system"
): AntragMeta {
  const all = readAllMeta();
  const current = getMeta(antrag_id);
  const old = current.status;

  // Erstes Mal: created-Eintrag
  if (!all[antrag_id]) {
    appendAudit(antrag_id, "created", null, "eingegangen", null, user);
  }

  if (old !== newStatus) {
    appendAudit(antrag_id, "status_changed", old, newStatus, comment || null, user);
  }

  const meta: AntragMeta = {
    antrag_id,
    status: newStatus,
    note: current.note,
    updated_at: new Date().toISOString(),
  };
  all[antrag_id] = meta;
  writeAllMeta(all);
  return meta;
}

export function setNote(
  antrag_id: string,
  note: string,
  user: string = "system"
): AntragMeta {
  const all = readAllMeta();
  const current = getMeta(antrag_id);
  const old = current.note;

  if (!all[antrag_id]) {
    appendAudit(antrag_id, "created", null, "eingegangen", null, user);
  }

  if (old !== note) {
    appendAudit(
      antrag_id,
      old ? "note_updated" : "note_added",
      old || null,
      note || null,
      null,
      user
    );
  }

  const meta: AntragMeta = {
    antrag_id,
    status: current.status,
    note,
    updated_at: new Date().toISOString(),
  };
  all[antrag_id] = meta;
  writeAllMeta(all);
  return meta;
}

// ---------- Verifikation der Hash-Kette ----------
export function verifyAuditChain(antrag_id: string): {
  valid: boolean;
  brokenAt: number | null;
} {
  const trail = getAuditTrail(antrag_id);
  let prev = "0".repeat(8);
  for (let i = 0; i < trail.length; i++) {
    const e = trail[i];
    if (e.prev_hash !== prev) return { valid: false, brokenAt: i };
    const { hash, ...rest } = e;
    const expected = simpleHash(JSON.stringify(rest));
    if (expected !== hash) return { valid: false, brokenAt: i };
    prev = hash;
  }
  return { valid: true, brokenAt: null };
}
