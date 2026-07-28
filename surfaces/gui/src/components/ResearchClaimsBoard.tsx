import type { ResearchRun } from "../api";

const STATUS_LABELS = {
  proposed: "Proposed",
  supported: "Supported",
  partial: "Partially supported",
  conflicting: "Conflicting",
  unsupported: "Unsupported",
} as const;

export function ResearchClaimsBoard({ run }: { run: ResearchRun }) {
  if (run.method !== "grounded_claims") return null;

  const claims = run.claims || [];
  const supported = claims.filter((claim) => claim.status === "supported").length;
  const coverage = claims.length ? Math.round((supported / claims.length) * 100) : 0;

  return (
    <details className="research-claims-board" open={claims.length > 0}>
      <summary>
        <span>Claim Ledger ({claims.length})</span>
        {claims.length > 0 && <span>{coverage}% fully supported</span>}
      </summary>
      {claims.length === 0 ? (
        <p>
          Claims will appear after the grounded report and its claim ledger are
          completed.
        </p>
      ) : (
        <div className="research-claim-list">
          {claims.map((claim) => (
            <article className={`research-claim ${claim.status}`} key={claim.claim_id}>
              <div>
                <strong>{claim.claim_id}</strong>
                <span>{STATUS_LABELS[claim.status]}</span>
                <span>{Math.round(claim.confidence * 100)}% confidence</span>
              </div>
              <p>{claim.claim}</p>
              <small>
                {claim.sources.length} source{claim.sources.length === 1 ? "" : "s"}
                {claim.justification ? ` · ${claim.justification}` : ""}
              </small>
              {claim.counterevidence && (
                <small className="research-claim-counter">
                  Counterevidence: {claim.counterevidence}
                </small>
              )}
            </article>
          ))}
        </div>
      )}
    </details>
  );
}
