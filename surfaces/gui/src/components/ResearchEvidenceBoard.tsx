import { useEffect, useState } from "react";
import {
  updateResearchEvidence,
  type ResearchEvidence,
  type ResearchRun,
} from "../api";

const STATUS_LABELS: Record<ResearchEvidence["status"], string> = {
  collected: "Collected",
  verified: "Verified",
  conflicting: "Conflicting",
  discarded: "Discarded",
};

function evidenceHost(url: string): string {
  try {
    return new URL(url).hostname || url;
  } catch {
    return url;
  }
}

export function ResearchEvidenceBoard({
  sessionId,
  run,
  onEvidenceUpdated,
}: {
  sessionId: string;
  run: ResearchRun;
  onEvidenceUpdated: (evidence: ResearchEvidence) => void;
}) {
  const [editingId, setEditingId] = useState("");
  const [note, setNote] = useState("");
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setEditingId("");
    setNote("");
    setError("");
  }, [run.run_id]);

  if (!run.evidence?.length) return null;

  const save = async (
    item: ResearchEvidence,
    changes: { status?: ResearchEvidence["status"]; note?: string },
  ) => {
    if (busyId) return;
    setBusyId(item.evidence_id);
    setError("");
    try {
      const result = await updateResearchEvidence(
        sessionId,
        run.run_id,
        item.evidence_id,
        changes,
      );
      if (!result.ok || !result.evidence) {
        setError(result.error || "Could not update this evidence.");
        return;
      }
      onEvidenceUpdated(result.evidence);
      if (changes.note !== undefined) setEditingId("");
    } catch {
      setError("Could not reach the local research service.");
    } finally {
      setBusyId("");
    }
  };

  return (
    <details className="research-evidence-board">
      <summary>Evidence ({run.evidence.length})</summary>
      <div className="research-evidence-list">
        {run.evidence.map((item) => (
          <article className="research-evidence-item" key={item.evidence_id}>
            <div className="research-evidence-head">
              <strong title={item.url}>
                {item.title || evidenceHost(item.url)}
              </strong>
              <select
                aria-label={`Evidence status for ${item.title || item.url}`}
                value={item.status}
                disabled={busyId === item.evidence_id}
                onChange={(event) =>
                  save(item, {
                    status: event.target.value as ResearchEvidence["status"],
                  })
                }
              >
                {(Object.keys(STATUS_LABELS) as ResearchEvidence["status"][]).map(
                  (status) => (
                    <option value={status} key={status}>
                      {STATUS_LABELS[status]}
                    </option>
                  ),
                )}
              </select>
            </div>
            <span title={item.url}>{evidenceHost(item.url)}</span>
            <span>
              {item.action || "browser capture"} ·{" "}
              {new Date(item.captured_at).toLocaleString()}
              {item.screenshot_sha256 ? " · snapshot recorded" : ""}
            </span>
            {editingId === item.evidence_id ? (
              <div className="research-evidence-note-editor">
                <textarea
                  aria-label="Evidence note"
                  value={note}
                  maxLength={2000}
                  onChange={(event) => setNote(event.target.value)}
                  rows={2}
                />
                <button
                  className="btn secondary"
                  disabled={busyId === item.evidence_id}
                  onClick={() => save(item, { note })}
                >
                  Save note
                </button>
              </div>
            ) : (
              <button
                className="research-evidence-note"
                onClick={() => {
                  setEditingId(item.evidence_id);
                  setNote(item.note || "");
                }}
              >
                {item.note || "Add note"}
              </button>
            )}
          </article>
        ))}
        {error && <div className="research-modal-error">{error}</div>}
      </div>
    </details>
  );
}
