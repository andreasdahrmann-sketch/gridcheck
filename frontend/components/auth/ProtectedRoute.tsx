"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { me, type AuthUser } from "@/lib/api/auth";

type ProtectedRouteProps = {
  children: ReactNode;
  requireAdmin?: boolean;
};

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);

  useEffect(() => {
    let active = true;

    me()
      .then((nextUser) => {
        if (active) {
          setUser(nextUser);
        }
      })
      .catch(() => {
        if (active) {
          setUser(null);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (user === undefined) {
      return;
    }
    if (user === null) {
      const next = encodeURIComponent(pathname || "/projects");
      router.replace(`/login?next=${next}`);
      return;
    }
    if (requireAdmin && user.role !== "admin") {
      router.replace("/");
    }
  }, [user, requireAdmin, pathname, router]);

  if (user === undefined) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center px-4 text-sm text-text-muted">
        Sitzung wird geprueft...
      </div>
    );
  }

  if (!user || (requireAdmin && user.role !== "admin")) {
    return null;
  }

  return <>{children}</>;
}
