const LABELS = {
  rapport: "Rapport",
  discovery: "Discovery",
  value_presentation: "Value presentation",
  objection_handling: "Objection handling",
  closing: "Closing",
};

export default function Evaluation({ evaluation, onRestart }) {
  return (
    <div className="card">
      <h2>Your performance: {evaluation.overall}/10</h2>
      {evaluation.outcome && <p className="muted">Outcome: {evaluation.outcome}</p>}
      <p>{evaluation.summary}</p>

      {Object.entries(evaluation.scores).map(([key, value]) => (
        <div className="score" key={key}>
          <span>{LABELS[key] || key}</span>
          <div className="bar"><div style={{ width: `${value * 10}%` }} /></div>
          <span>{value}/10</span>
        </div>
      ))}

      <h3>Strengths</h3>
      <ul>{evaluation.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
      <h3>To improve</h3>
      <ul>{evaluation.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>

      <button onClick={onRestart}>Practice again</button>
    </div>
  );
}
