"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { register } from "@/lib/api/auth";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("endkunde");
  const [fullName, setFullName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await register({ email, password, role, full_name: fullName });
      setMessage("Registrierung erfolgreich. Bitte einloggen.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registrierung fehlgeschlagen");
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="max-w-md mx-auto p-6">
        <h1 className="text-2xl font-semibold mb-4">Registrierung</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="Name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="E-Mail" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="Passwort" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <select className="w-full p-2 rounded bg-bg-elev" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="endkunde">Endkunde</option>
            <option value="projektierer">Projektierer</option>
            <option value="netzbetreiber">Netzbetreiber</option>
          </select>
          {message ? <p className="text-green-400 text-sm">{message}</p> : null}
          {error ? <p className="text-red-400 text-sm">{error}</p> : null}
          <button className="w-full bg-brand-orange rounded p-2 font-semibold">Konto anlegen</button>
        </form>
        <p className="text-sm text-text-muted mt-4">
          Bereits registriert? <Link className="text-brand-cyan" href="/login">Zum Login</Link>
        </p>
      </div>
    </main>
  );
}
