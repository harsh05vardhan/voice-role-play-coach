import { useEffect, useRef, useState } from "react";

export default function Call({ sessionId, onFinish }) {
  const [messages, setMessages] = useState([]); // {role: "you" | "customer", text}
  const [status, setStatus] = useState("connecting"); // connecting | idle | recording | thinking | speaking
  const [error, setError] = useState("");
  const [typed, setTyped] = useState("");
  const [ending, setEnding] = useState(false);

  const ws = useRef(null);
  const recorder = useRef(null);
  const customerOpen = useRef(false); // is the current customer bubble still being filled?
  const queue = useRef([]); // MP3 blobs waiting to be played
  const playing = useRef(false);
  const turnDone = useRef(true);
  const logEnd = useRef(null);

  useEffect(() => {
    logEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function playNext() {
    if (playing.current) return;
    const blob = queue.current.shift();
    if (!blob) {
      if (turnDone.current) setStatus("idle");
      return;
    }
    playing.current = true;
    setStatus("speaking");
    const audio = new Audio(URL.createObjectURL(blob));
    const next = () => {
      playing.current = false;
      playNext();
    };
    audio.onended = next;
    audio.onerror = next;
    audio.play().catch(next);
  }

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${proto}://${location.host}/ws/${sessionId}`);
    ws.current = socket;
    socket.onopen = () => setStatus("idle");
    socket.onclose = () => setStatus("connecting");
    socket.onmessage = (e) => {
      if (e.data instanceof Blob) {
        queue.current.push(e.data);
        playNext();
        return;
      }
      const m = JSON.parse(e.data);
      if (m.type === "transcript") {
        setMessages((prev) => [...prev, { role: "you", text: m.text }]);
        setStatus("thinking");
      } else if (m.type === "reply_text") {
        if (customerOpen.current) {
          setMessages((prev) => {
            const copy = [...prev];
            const last = copy[copy.length - 1];
            copy[copy.length - 1] = { ...last, text: last.text + " " + m.text };
            return copy;
          });
        } else {
          customerOpen.current = true;
          setMessages((prev) => [...prev, { role: "customer", text: m.text }]);
        }
      } else if (m.type === "error") {
        setError(m.message);
      } else if (m.type === "done") {
        customerOpen.current = false;
        turnDone.current = true;
        if (!playing.current && queue.current.length === 0) setStatus("idle");
      }
    };
    return () => socket.close();
  }, [sessionId]);

  async function startRecording() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks = [];
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: rec.mimeType });
        const ext = rec.mimeType.includes("ogg") ? "ogg" : rec.mimeType.includes("mp4") ? "mp4" : "webm";
        ws.current.send(await blob.arrayBuffer());
        ws.current.send(JSON.stringify({ type: "end_audio", ext }));
        turnDone.current = false;
        setStatus("thinking");
      };
      rec.start();
      recorder.current = rec;
      setStatus("recording");
    } catch {
      setError("Microphone unavailable. Allow mic access, or type your message below.");
    }
  }

  function stopRecording() {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }

  function sendText(e) {
    e.preventDefault();
    const text = typed.trim();
    if (!text || ws.current?.readyState !== WebSocket.OPEN) return;
    setError("");
    ws.current.send(JSON.stringify({ type: "text", text }));
    turnDone.current = false;
    setStatus("thinking");
    setTyped("");
  }

  async function endSession() {
    setEnding(true);
    setError("");
    try {
      const res = await fetch(`/api/sessions/${sessionId}/evaluate`, { method: "POST" });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Evaluation failed");
      ws.current?.close();
      onFinish(body);
    } catch (err) {
      setError(err.message);
      setEnding(false);
    }
  }

  const busy = status === "thinking" || status === "connecting";
  const labels = {
    connecting: "Connecting…",
    idle: "Your turn",
    recording: "Listening… click to stop",
    thinking: "Customer is thinking…",
    speaking: "Customer is speaking…",
  };

  return (
    <div className="card">
      <div className="log">
        {messages.length === 0 && <p className="muted">Introduce yourself to the customer to begin.</p>}
        {messages.map((m, i) => (
          <p key={i} className={m.role}>
            <strong>{m.role === "you" ? "You" : "Customer"}:</strong> {m.text}
          </p>
        ))}
        <div ref={logEnd} />
      </div>
      <p className="status">{labels[status]}</p>
      {error && <p className="error">{error}</p>}
      <div className="controls">
        {status === "recording" ? (
          <button className="rec" onClick={stopRecording}>■ Stop &amp; send</button>
        ) : (
          <button onClick={startRecording} disabled={busy || ending}>🎤 Speak</button>
        )}
        <button className="secondary" onClick={endSession} disabled={ending || messages.length === 0}>
          {ending ? "Evaluating…" : "End session & get feedback"}
        </button>
      </div>
      <form className="typed" onSubmit={sendText}>
        <input
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder="…or type your message"
          disabled={busy || ending || status === "recording"}
        />
        <button type="submit" disabled={busy || ending || !typed.trim()}>Send</button>
      </form>
    </div>
  );
}
