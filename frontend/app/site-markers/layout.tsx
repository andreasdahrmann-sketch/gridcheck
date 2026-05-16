import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

export default function SiteMarkersLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
