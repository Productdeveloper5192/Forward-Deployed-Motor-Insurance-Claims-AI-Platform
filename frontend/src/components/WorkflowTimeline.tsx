import { titleCase } from "../lib/format";
import type { WorkflowRunOut } from "../api/types";

function summarize(outputJson: string | null): { isError: boolean; text: string } {
  if (!outputJson) return { isError: false, text: "" };
  try {
    const parsed = JSON.parse(outputJson);
    if (parsed && typeof parsed === "object" && "error" in parsed) {
      return { isError: true, text: String(parsed.error) };
    }
    return { isError: false, text: JSON.stringify(parsed, null, 2) };
  } catch {
    return { isError: false, text: outputJson };
  }
}

export function WorkflowTimeline({ run }: { run: WorkflowRunOut }) {
  if (run.node_executions.length === 0 && run.status === "running") {
    return <p className="page-sub">Starting the AI pipeline…</p>;
  }

  return (
    <div className="timeline">
      {run.node_executions.map((node, idx) => {
        const { isError, text } = summarize(node.output_json);
        const isLast = idx === run.node_executions.length - 1;
        return (
          <div className="timeline-node" key={`${node.node_name}-${idx}`}>
            <div className="timeline-dot-col">
              <div className={`timeline-dot ${isError ? "error" : ""}`} />
              {!isLast && <div className="timeline-line" />}
            </div>
            <div className="timeline-body">
              <div className="timeline-name">{titleCase(node.node_name)}</div>
              <div className="timeline-meta">{node.duration_ms.toLocaleString()} ms</div>
              {text && <div className="timeline-output">{text}</div>}
            </div>
          </div>
        );
      })}
      {run.status === "running" && run.current_node && (
        <div className="timeline-node">
          <div className="timeline-dot-col">
            <div className="timeline-dot pending" />
          </div>
          <div className="timeline-body">
            <div className="timeline-name">{titleCase(run.current_node)}</div>
            <div className="timeline-meta">running…</div>
          </div>
        </div>
      )}
      {run.status === "failed" && run.error && (
        <div className="timeline-node">
          <div className="timeline-dot-col">
            <div className="timeline-dot error" />
          </div>
          <div className="timeline-body">
            <div className="timeline-name">Workflow failed</div>
            <div className="timeline-output">{run.error}</div>
          </div>
        </div>
      )}
    </div>
  );
}
