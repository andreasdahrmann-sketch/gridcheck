import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}
