import type { GridCheckInput, GridCheckResult } from "@/types";
import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders } from "@/lib/api/session";

export type ProjectRoleInputs = Partial<GridCheckInput> & {
  kundentyp?: string;
  projektname?: string;
  erzeugungstyp?: string;
};

export type Project = {
  id: number;
  name: string;
  plz: string | null;
  ort?: string | null;
  street?: string | null;
  house_number?: string | null;
  city?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  typ: string;
  leistung_kw: number;
  description?: string | null;
  role_inputs: ProjectRoleInputs;
  role_results: Partial<GridCheckResult>;
  owner_user_id?: number | null;
  created_at?: string;
  updated_at?: string | null;
  warnings?: string[];
};

const BASE = "/api/backend/api/v1/projects";

export class ProjectsApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ProjectsApiError";
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ProjectsApiError(body?.detail?.message ?? "API request failed", res.status);
  }
  return res.json() as Promise<T>;
}

export async function listProjects() {
  const res = await fetch(BASE, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<Project[]>(res);
}

export async function getProject(projectId: number) {
  const res = await fetch(`${BASE}/${projectId}`, {
    credentials: "include",
    cache: "no-store",
    headers: { ...bearerAuthHeaders() },
  });
  return parse<Project>(res);
}

export async function createProject(
  payload: {
    name: string;
    plz?: string | null;
    ort?: string | null;
    street?: string | null;
    house_number?: string | null;
    city?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    typ: string;
    leistung_kw: number;
    description?: string;
    role_inputs?: ProjectRoleInputs;
    role_results?: Partial<GridCheckResult>;
  }
) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(BASE, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify(payload),
  });
  return parse<Project>(res);
}

export async function updateProject(projectId: number, payload: Partial<Project>) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/${projectId}`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify(payload),
  });
  return parse<Project>(res);
}

export async function deleteProject(projectId: number) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/${projectId}`, {
    method: "DELETE",
    credentials: "include",
    headers: { ...bearerAuthHeaders(), ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
  });
  return parse<{ status: string }>(res);
}

export async function shareProject(projectId: number, target_user_id: number, project_role: string) {
  const csrf = getCsrfTokenFromCookie();
  const res = await fetch(`${BASE}/${projectId}/share`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...bearerAuthHeaders(),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify({ target_user_id, project_role }),
  });
  return parse<{ status: string }>(res);
}
