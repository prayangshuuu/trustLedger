import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Json } from "../lib/api";
import { motion, useAppState } from "../lib/state";
import { Icon, Spinner, TLScaffold, useShowError } from "../ui";

const pipelineSteps = ["data_agent", "bhorsha_router", "scoring_agent", "explainer_agent", "fairness_agent", "finalize"];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function Processing() {
  const s = useAppState();
  const navigate = useNavigate();
  const showError = useShowError(s);
  const [done, setDone] = useState<Record<string, number>>({});
  const [error, setError] = useState<unknown>(null);
  const alive = useRef(true);

  const run = useCallback(async () => {
    setError(null);
    const stepDelay = motion(350);
    try {
      const result = await s.runApply();
      // Reveal the agent steps one by one so the user sees what happened
      for (const step of (result.trace ?? []) as Json[]) {
        await sleep(stepDelay);
        if (!alive.current) return;
        setDone((d) => ({ ...d, [step.node]: Number(step.ms) }));
      }
      await sleep(stepDelay);
      if (!alive.current) return;
      if (result.status === "bhorsha_required") navigate("/bhorsha", { replace: true });
      else if (result.decision != null) navigate("/score", { replace: true });
      else setError(result.error ?? "error");
    } catch (e) {
      if (!alive.current) return;
      setError(e);
      showError(e, run);
    }
  }, [s, navigate, showError]);

  const started = useRef(false);
  useEffect(() => {
    alive.current = true;
    if (!started.current) {
      started.current = true; // StrictMode mounts twice in dev; apply once
      run();
    }
    return () => {
      alive.current = false;
    };
  }, [run]);

  return (
    <TLScaffold state={s} title={s.t("processing")}>
      {pipelineSteps.map((step) => (
        <div className="tile" key={step} data-testid={`step_${step}`}>
          {step in done ? <Icon name="check_circle" color="var(--good)" label="done" /> : <Spinner />}
          <div className="tile-text"><div className="tile-title">{s.t(`step_${step}`)}</div></div>
          {step in done && <span>{`${done[step].toFixed(0)} ms`}</span>}
        </div>
      ))}
      {error != null && (
        <button className="btn btn-filled mt-lg" onClick={run}>{s.t("retry")}</button>
      )}
    </TLScaffold>
  );
}
