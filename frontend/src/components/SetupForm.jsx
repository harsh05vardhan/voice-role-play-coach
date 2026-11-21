import { useEffect, useState } from "react";

export default function SetupForm({ onStart }) {
  const [options, setOptions] = useState(null);
  const [form, setForm] = useState({ scenario: "", personality: "", difficulty: "medium", budget: 5000 });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/options")
      .then((r) => r.json())
      .then((o) => {
        setOptions(o);
        setForm((f) => ({ ...f, scenario: o.scenarios[0].id, personality: o.personalities[0].id }));
      })
      .catch(() => setError("Cannot reach the backend. Is it running on port 8000?"));
  }, []);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, budget: Number(form.budget) }),
      });
      if (!res.ok) throw new Error("Could not create session (check the budget is a positive number).");
      const { session_id } = await res.json();
      onStart(session_id);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  if (!options) return <p>{error || "Loading…"}</p>;

  const persona = options.personalities.find((p) => p.id === form.personality);

  return (
    <form className="card" onSubmit={submit}>
      <h2>Set up your practice call</h2>
      <label>
        Product / scenario
        <select value={form.scenario} onChange={set("scenario")}>
          {options.scenarios.map((s) => (
            <option key={s.id} value={s.id}>{s.title}</option>
          ))}
        </select>
      </label>
      <label>
        Customer personality
        <select value={form.personality} onChange={set("personality")}>
          {options.personalities.map((p) => (
            <option key={p.id} value={p.id}>{p.title}</option>
          ))}
        </select>
        <small>{persona?.description}</small>
      </label>
      <label>
        Customer budget ($)
        <input type="number" min="1" value={form.budget} onChange={set("budget")} />
      </label>
      <label>
        Difficulty
        <select value={form.difficulty} onChange={set("difficulty")}>
          {options.difficulties.map((d) => (
            <option key={d.id} value={d.id}>{d.title}</option>
          ))}
        </select>
      </label>
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={loading}>{loading ? "Starting…" : "Start call"}</button>
    </form>
  );
}
