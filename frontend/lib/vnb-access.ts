import type { AuthUser } from "@/lib/api/auth";

export type VnbVerificationStatus = "none" | "pending" | "approved";

export type VnbAccessState =
  | "verified"
  | "pending"
  | "wrong_role"
  | "not_registered";

export function resolveVnbAccessState(user: AuthUser | null | undefined): VnbAccessState {
  if (!user) return "not_registered";
  if (user.vnb_dashboard_access || user.role === "admin" || user.netzbetreiber_verified) {
    return "verified";
  }
  if (user.role !== "netzbetreiber") return "wrong_role";
  if (user.vnb_verification_status === "pending") return "pending";
  return "not_registered";
}

export function canAccessVnbDashboard(user: AuthUser | null | undefined): boolean {
  return resolveVnbAccessState(user) === "verified";
}

export function vnbAccessMessage(state: VnbAccessState): { title: string; body: string } {
  switch (state) {
    case "pending":
      return {
        title: "Freischaltung ausstehend",
        body:
          "Ihre Identitaet als Netzbetreiber wird geprueft. Der Zugang zum VNB-Dashboard wird nach Freischaltung freigegeben.",
      };
    case "wrong_role":
      return {
        title: "Nur fuer Netzbetreiber",
        body:
          "Dieses Dashboard ist nur fuer Netzbetreiber. Registrieren Sie sich mit Rolle Netzbetreiber und lassen Sie sich freischalten.",
      };
    default:
      return {
        title: "Zugang nicht freigeschaltet",
        body:
          "Dieses Dashboard ist nur fuer freigeschaltete Netzbetreiber. Registrieren Sie sich mit Rolle Netzbetreiber und lassen Sie sich freischalten.",
      };
  }
}
