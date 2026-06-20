import { useCallback, useEffect, useState } from "react";
import "./ProjectTracker.css";
import { type ProjectPlan, zProjectPlan } from "./projectPlanSchema";

type State =
  | { status: "loading" }
  | { status: "ready"; data: ProjectPlan }
  | { status: "error" };

export function ProjectTracker() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const res = await fetch("/api/internal/project-plan");
      const data = zProjectPlan.parse(await res.json());
      setState({ status: "ready", data });
    } catch {
      setState({ status: "error" });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state.status === "loading")
    return <p className="dg-tracker__msg">Loading project plan…</p>;
  if (state.status === "error")
    return <p className="dg-tracker__msg">Could not load the project plan.</p>;

  const { data } = state;
  return (
    <div className="dg-tracker">
      <div className="dg-tracker__bar">
        <span>Updated: {data.updated_at ?? "—"}</span>
        <button type="button" onClick={() => void load()}>
          Refresh
        </button>
      </div>
      {data.warnings.length > 0 && (
        <ul className="dg-tracker__warnings" role="status">
          {data.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      {data.phases.length === 0 ? (
        <p className="dg-tracker__msg">No project plan available.</p>
      ) : (
        data.phases.map((p) => (
          <section key={p.id} className="dg-tracker__phase">
            <button
              type="button"
              className="dg-tracker__phase-head"
              aria-expanded={!!open[p.id]}
              onClick={() => setOpen((o) => ({ ...o, [p.id]: !o[p.id] }))}
            >
              <span className="dg-tracker__badge" data-status={p.status}>
                {p.status}
              </span>
              {p.title}
            </button>
            {open[p.id] && (
              <ul className="dg-tracker__tasks">
                {p.tasks.map((t) => (
                  <li key={t.id}>
                    <span className="dg-tracker__badge" data-status={t.status}>
                      {t.status}
                    </span>
                    {t.title}
                    {t.note ? <em> — {t.note}</em> : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))
      )}
    </div>
  );
}
