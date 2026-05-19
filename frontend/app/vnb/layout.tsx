import { ProtectedVnbRoute } from "@/components/auth/ProtectedVnbRoute";

export default function VnbLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedVnbRoute>{children}</ProtectedVnbRoute>;
}
