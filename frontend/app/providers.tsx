"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";
import { PwaBootstrap } from "@/components/mobile/PwaBootstrap";
import { IdleLogoutGate } from "@/components/auth/IdleLogoutGate";

export default function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <PwaBootstrap />
      <IdleLogoutGate />
      {children}
    </QueryClientProvider>
  );
}
