"use client";

import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: form.get("email"),
        password: form.get("password"),
      }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      setError(payload.error ?? "Não foi possível entrar.");
      setLoading(false);
      return;
    }
    const destination = new URLSearchParams(window.location.search).get("next");
    window.location.href = destination || "/monitor_vip.html";
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="login-mark">VIP</div>
        <p className="login-kicker">VF INTELLIGENCE PLATFORM</p>
        <h1>GSB Monitor</h1>
        <p className="login-copy">Acesso privado ao ambiente de oportunidades e operação comercial.</p>
        <form onSubmit={submit}>
          <label>
            E-mail
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            Senha
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          {error ? <p className="login-error">{error}</p> : null}
          <button type="submit" disabled={loading}>
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
