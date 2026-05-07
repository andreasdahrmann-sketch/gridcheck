"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { login } from "@/lib/api/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login({ email, password });
      window.location.href = "/projects";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login fehlgeschlagen");
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="max-w-md mx-auto p-6">
        <h1 className="text-2xl font-semibold mb-4">Login</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="E-Mail" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="Passwort" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error ? <p className="text-red-400 text-sm">{error}</p> : null}
          <button className="w-full bg-brand-orange rounded p-2 font-semibold">Einloggen</button>
        </form>
        <p className="text-sm text-text-muted mt-4">
          Noch kein Konto? <Link className="text-brand-cyan" href="/register">Registrieren</Link>
        </p>
      </div>
    </main>
  );
}
