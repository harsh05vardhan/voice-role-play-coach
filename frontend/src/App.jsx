import { useState } from "react";
import SetupForm from "./components/SetupForm.jsx";
import Call from "./components/Call.jsx";
import Evaluation from "./components/Evaluation.jsx";

export default function App() {
  const [stage, setStage] = useState("setup"); // setup | call | result
  const [sessionId, setSessionId] = useState(null);
  const [evaluation, setEvaluation] = useState(null);

  return (
    <main className="container">
      <h1>Voice Role-Play Coach</h1>
      {stage === "setup" && (
        <SetupForm
          onStart={(id) => {
            setSessionId(id);
            setStage("call");
          }}
        />
      )}
      {stage === "call" && (
        <Call
          sessionId={sessionId}
          onFinish={(result) => {
            setEvaluation(result);
            setStage("result");
          }}
        />
      )}
      {stage === "result" && (
        <Evaluation
          evaluation={evaluation}
          onRestart={() => {
            setEvaluation(null);
            setSessionId(null);
            setStage("setup");
          }}
        />
      )}
    </main>
  );
}
