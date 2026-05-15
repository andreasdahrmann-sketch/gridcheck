import { AnalyzeApiError } from "@/lib/api/analyze";
import { getCsrfTokenFromCookie } from "@/lib/api/csrf";

const BASE = "/api/backend/api/v1/ki";

export type KiFeedbackType = "bestaetigt" | "korrigiert";
export type KiDecision = "A" | "B" | "C";

export type SubmitKiFeedbackPayload = {
  feedback_typ: KiFeedbackType;
  ki_entscheidung: KiDecision;
  nb_entscheidung?: KiDecision;
  kommentar?: string;
  revision_hash?: string;
  score_gesamt?: number;
  confidence_snapshot?: number;
  anomaly_flags?: string[];
  quelle?: "netzbetreiber" | "audit" | "manuell";
};

export type SubmitKiFeedbackResponse = {
  status: string;
  feedback: {
    feedback_nummer: number;
    hash: string;
    feedback_typ: KiFeedbackType;
    revision_hash?: string;
  };
  kalibrierung: {
    samples: number;
    kalibrierungsfaktor: number;
    trefferquote: number;
    bestaetigungsquote?: number;
    status: string;
  };
  lernstatus: {
    samples_total: number;
    linked_samples: number;
    bestaetigt: number;
    korrigiert: number;
    bestaetigungsquote: number;
    status: string;
  };
  audit_revision?: {
    hash?: string;
    revisionsnummer?: number;
  };
};

export async function submitKiFeedback(
  payload: SubmitKiFeedbackPayload
): Promise<SubmitKiFeedbackResponse> {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/feedback`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify(payload),
  });

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    const message =
      typeof detail?.message === "string"
        ? detail.message
        : typeof detail === "string"
          ? detail
          : `KI-Feedback fehlgeschlagen (HTTP ${res.status})`;
    throw new AnalyzeApiError(
      res.status,
      message,
      detail && typeof detail === "object" && !Array.isArray(detail) ? detail : null
    );
  }

  return body as SubmitKiFeedbackResponse;
}
