import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";

export default function MapLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}
