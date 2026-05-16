import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

export default function OpsLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute requireAdmin>{children}</ProtectedRoute>;
}
