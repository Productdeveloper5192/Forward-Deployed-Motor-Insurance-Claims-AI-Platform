import { titleCase } from "../lib/format";
import type { ClaimStatus } from "../api/types";

const TONE: Record<ClaimStatus, string> = {
  draft: "neutral",
  submitted: "accent",
  processing: "accent",
  needs_review: "warn",
  approved: "good",
  denied: "bad",
  paid: "good",
  failed: "bad",
};

export function StatusBadge({ status }: { status: ClaimStatus }) {
  return <span className={`badge ${TONE[status] ?? "neutral"}`}>{titleCase(status)}</span>;
}
