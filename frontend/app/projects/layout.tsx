import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

export default function ProjectsLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>;
}
