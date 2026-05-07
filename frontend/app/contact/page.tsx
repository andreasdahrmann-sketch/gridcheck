"use client";

import { FormEvent, useState } from "react";
import { Header } from "@/components/Header";
import { submitContact } from "@/lib/api/contact";

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setResult(null);
    try {
      await submitContact({ name, email, subject, message });
      setResult("Nachricht wurde gesendet.");
      setMessage("");
    } catch (err) {
      setResult(err instanceof Error ? err.message : "Senden fehlgeschlagen.");
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-semibold mb-4">Kontakt</h1>
        <form onSubmit={onSubmit} className="space-y-3">
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="E-Mail" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="Betreff" value={subject} onChange={(e) => setSubject(e.target.value)} required />
          <textarea className="w-full p-2 rounded bg-bg-elev" rows={6} placeholder="Nachricht" value={message} onChange={(e) => setMessage(e.target.value)} required />
          {result ? <p className="text-sm text-brand-cyan">{result}</p> : null}
          <button className="bg-brand-orange rounded p-2 px-4 font-semibold">Senden</button>
        </form>
      </div>
    </main>
  );
}
