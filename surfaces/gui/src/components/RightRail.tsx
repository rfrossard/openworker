import { useEffect, useRef, useState, type ReactNode } from "react";
// Emits the asset URL only; the worker itself loads lazily with the pdfjs chunk.
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import {
  analyzeBrowserStreamingMedia,
  cancelBrowserStreamingMedia,
  closeBrowser,
  downloadBrowserMedia,
  downloadBrowserStreamingMedia,
  getArtifacts,
  getBrowserState,
  getResearchRuns,
  getSettings,
  performBrowserHumanAction,
  readArtifact,
  revealArtifact,
  setBrowserControl,
  setBrowserPolicy,
  takeBrowserScreenshot,
  type ArtifactContent,
  type ArtifactInfo,
  type BrowserState,
  type ResearchRun,
} from "../api";
import type { TodoItem } from "../types";
import { AccessSection } from "./AccessSection";
import { DeepResearchLauncher } from "./DeepResearchLauncher";
import { Icon } from "./Icon";
import { Markdown, OPEN_ARTIFACT_EVENT } from "./Markdown";
import { ResearchEvidenceBoard } from "./ResearchEvidenceBoard";
import { ResearchClaimsBoard } from "./ResearchClaimsBoard";
import { MarkdownPdfLauncher } from "./MarkdownPdfLauncher";
import { ManusPresentationLauncher } from "./ManusPresentationLauncher";
import { MarkdownSlideDesigner } from "./MarkdownSlideDesigner";

type Panel = "progress" | "browser" | "artifacts";

// Quiet file-type icons for the artifact list (the colored kind pills read as noisy).
function kindIcon(kind: string): "file" | "fileCode" | "image" | "table" {
  if (kind === "image") return "image";
  if (kind === "html" || kind === "code") return "fileCode";
  if (kind === "csv" || kind === "sheet") return "table";
  return "file"; // markdown, text, pdf, everything else
}

// Fallback kind for an artifact: link whose path isn't in the list (yet) — mirrors the
// server's extension mapping closely enough for the viewer to pick a renderer.
function kindFromPath(path: string): string {
  const ext = (path.split(".").pop() || "").toLowerCase();
  if (["png", "jpg", "jpeg", "gif", "svg", "webp"].includes(ext)) return "image";
  if (["html", "htm"].includes(ext)) return "html";
  if (ext === "md") return "markdown";
  if (ext === "csv") return "csv";
  if (ext === "pdf") return "pdf";
  if (["py", "js", "ts", "tsx", "jsx", "json", "sh", "css"].includes(ext)) return "code";
  return "text";
}

interface Props {
  active: boolean;
  sessionId: string;
  refreshKey: number;
  toolNames: string[];
  todo: TodoItem[];
  running: boolean;
  // Fires when a full artifact preview opens/closes, so the app can auto-collapse the left nav
  // to give the preview (PDF/webpage/sheet) more room (#3).
  onPreviewChange?: (open: boolean) => void;
  // §32: the rail is the ONE session panel for every non-chat persona. Artifacts stays
  // cowork-only (deliverables; code-family gets "Files" later — slot reserved); the Access
  // section (the former Session-settings drawer) renders for all.
  showArtifacts?: boolean;
  personaId?: string;
  projectScoped?: boolean;
  workspace?: string;
  branch?: string | null;
  scratchPrimary?: boolean;
  openAccessKey?: number;
  onOpenIntegrations?: () => void;
  onResearchPrefill?: (prompt: string) => void;
}

export function RightRail({
  active,
  sessionId,
  refreshKey,
  toolNames,
  todo,
  running,
  onPreviewChange,
  showArtifacts = true,
  personaId,
  projectScoped,
  workspace,
  branch,
  scratchPrimary,
  openAccessKey = 0,
  onOpenIntegrations,
  onResearchPrefill,
}: Props) {
  const [open, setOpen] = useState<Record<Panel, boolean>>({
    progress: true,
    browser: true,
    artifacts: true,
  });
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [selected, setSelected] = useState<ArtifactInfo | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);
  const [researchRuns, setResearchRuns] = useState<ResearchRun[]>([]);
  const [editingResearchRun, setEditingResearchRun] = useState<ResearchRun | null>(null);

  const refreshArtifacts = () => getArtifacts(sessionId).then(setArtifacts).catch(() => setArtifacts([]));
  const refreshResearchRuns = () => getResearchRuns(sessionId).then(setResearchRuns).catch(() => setResearchRuns([]));

  useEffect(() => {
    if (!active) return;
    if (showArtifacts) refreshArtifacts();
    if (showArtifacts) refreshResearchRuns();
  }, [active, sessionId, refreshKey, showArtifacts]);

  // Switching conversations closes any open artifact — it belongs to the previous session's
  // workspace, which the new session can't (and shouldn't) read.
  useEffect(() => {
    setSelected(null);
    setContent(null);
    setEditingResearchRun(null);
  }, [sessionId]);

  useEffect(() => {
    setContent(null);
    if (!selected) return;
    readArtifact(sessionId, selected.path).then(setContent).catch(() => setContent(null));
  }, [selected?.path, sessionId]);

  // Notify the app when a preview opens/closes (drives the left-nav auto-collapse).
  useEffect(() => {
    onPreviewChange?.(!!selected);
  }, [!!selected, onPreviewChange]);

  const reloadSelected = () => {
    if (!selected) return Promise.resolve();
    setContent(null);
    return readArtifact(sessionId, selected.path).then(setContent).catch(() => setContent(null));
  };

  // §34 (UX-016): [Title](artifact:path) chips in the transcript open the viewer directly.
  // Resolve against the loaded list first; on a miss, refresh once (the file may be
  // seconds old), then fall back to a minimal record — readArtifact validates the path.
  useEffect(() => {
    if (!active) return;
    const minimal = (path: string): ArtifactInfo => ({
      path,
      name: path.split("/").pop() || path,
      kind: kindFromPath(path),
      size: 0,
      modified_at: 0,
    });
    const match = (list: ArtifactInfo[], path: string) =>
      list.find((a) => a.path === path || a.path.endsWith("/" + path) || a.name === path);
    const onOpen = (e: Event) => {
      const path = String((e as CustomEvent).detail?.path || "");
      if (!path) return;
      const found = match(artifacts, path);
      if (found) {
        setSelected(found);
        return;
      }
      getArtifacts(sessionId)
        .then((list) => {
          setArtifacts(list);
          setSelected(match(list, path) ?? minimal(path));
        })
        .catch(() => setSelected(minimal(path)));
    };
    window.addEventListener(OPEN_ARTIFACT_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_ARTIFACT_EVENT, onOpen);
  }, [active, sessionId, artifacts]);

  if (!active) return null;

  return (
    <aside className={"right-rail" + (selected ? " artifact-mode" : "")}>
      {selected ? (
        <ArtifactViewer
          sessionId={sessionId}
          artifact={selected}
          content={content}
          onReload={reloadSelected}
          onBack={() => setSelected(null)}
        />
      ) : (
        <>
          <RailSection title="Progress" open={open.progress} onToggle={() => setOpen({ ...open, progress: !open.progress })}>
            <ProgressSummary running={running} toolNames={toolNames} todo={todo} />
          </RailSection>

          <BrowserOperator
            sessionId={sessionId}
            refreshKey={refreshKey}
            running={running}
            toolNames={toolNames}
            open={open.browser}
            onToggle={() => setOpen({ ...open, browser: !open.browser })}
          />

          {showArtifacts && (
          <RailSection
            title={`Artifacts${artifacts.length ? ` (${artifacts.length})` : ""}`}
            open={open.artifacts}
            onToggle={() => setOpen({ ...open, artifacts: !open.artifacts })}
            action={
              <>
                {artifacts.length > 0 && (
                  <button
                    className="rail-mini-btn"
                    onClick={(e) => { e.stopPropagation(); revealArtifact(sessionId, artifacts[0].path, "reveal"); }}
                    title="Show the folder where these files are saved"
                  >
                    <Icon name="folder" size={13} />
                  </button>
                )}
                <button className="rail-mini-btn" onClick={(e) => { e.stopPropagation(); refreshArtifacts(); }} title="Refresh artifacts"><Icon name="refresh" size={13} /></button>
              </>
            }
          >
            {onResearchPrefill && (
              <>
                <div className="artifact-studio-actions">
                  <DeepResearchLauncher
                    sessionId={sessionId}
                    artifacts={artifacts}
                    onCreate={onResearchPrefill}
                    editingRun={editingResearchRun}
                    onEditingClose={() => setEditingResearchRun(null)}
                    onRunCreated={(run) =>
                      setResearchRuns((current) => [
                        run,
                        ...current.filter((item) => item.run_id !== run.run_id),
                      ])
                    }
                  />
                  <MarkdownPdfLauncher
                    artifacts={artifacts}
                    onCreate={onResearchPrefill}
                  />
                  <ManusPresentationLauncher
                    artifacts={artifacts}
                    onCreate={onResearchPrefill}
                  />
                  <MarkdownSlideDesigner
                    sessionId={sessionId}
                    artifacts={artifacts}
                    onCreate={onResearchPrefill}
                  />
                </div>
              </>
            )}
            {researchRuns.length > 0 && (
              <div className="research-project-list" aria-label="Research projects">
                {researchRuns.slice(0, 5).map((run) => (
                  <div className="research-run-card" key={run.run_id}>
                    <div>
                      <span className={`research-run-status ${run.status}`}>
                        {run.status === "partially_completed" ? "partial" : run.status}
                      </span>
                      <strong title={run.question}>{run.question}</strong>
                      {run.status === "planned" && (
                        <button
                          className="research-project-edit"
                          onClick={() => setEditingResearchRun(run)}
                        >
                          Edit
                        </button>
                      )}
                    </div>
                    <span>
                      {run.depth} · {run.artifact_count} artifacts ·{" "}
                      {run.browser_navigation_count} pages
                    </span>
                    <span>
                      {run.deliverable === "presentation" ? "presentation" : "report"} ·{" "}
                      {run.method === "grounded_claims" ? "grounded claims" : "standard"} ·{" "}
                      {run.plan.length} plan steps · {run.source_limit} sources planned
                    </span>
                    {run.quality?.status === "passed" && (
                      <span className="research-quality passed">
                        Quality gate passed · {run.quality.checks} checks
                      </span>
                    )}
                    {run.quality?.status === "needs_attention" && (
                      <details className="research-quality needs-attention">
                        <summary>
                          Quality review · {run.quality.issues.length} issue
                          {run.quality.issues.length === 1 ? "" : "s"}
                        </summary>
                        <ul>
                          {run.quality.issues.map((issue) => <li key={issue}>{issue}</li>)}
                        </ul>
                      </details>
                    )}
                    <ResearchClaimsBoard run={run} />
                    <ResearchEvidenceBoard
                      sessionId={sessionId}
                      run={run}
                      onEvidenceUpdated={(evidence) =>
                        setResearchRuns((current) =>
                          current.map((item) =>
                            item.run_id === run.run_id
                              ? {
                                  ...item,
                                  evidence: item.evidence.map((value) =>
                                    value.evidence_id === evidence.evidence_id
                                      ? evidence
                                      : value,
                                  ),
                                }
                              : item,
                          ),
                        )
                      }
                    />
                  </div>
                ))}
              </div>
            )}
            {artifacts.length === 0 ? (
              <div className="rail-muted">No previewable files yet.</div>
            ) : (
              <div className="artifact-list">
                {artifacts.slice(0, 16).map((a) => (
                  <button className="artifact-row" key={a.path} onClick={() => setSelected(a)}>
                    <span className="artifact-ico" title={a.kind}>
                      <Icon name={kindIcon(a.kind)} size={17} />
                    </span>
                    <span className="artifact-name">
                      {a.name}
                      <span className="artifact-row-meta">{formatBytes(a.size)} · {formatTime(a.modified_at)}</span>
                    </span>
                    <span className="artifact-open">Open</span>
                  </button>
                ))}
              </div>
            )}
          </RailSection>
          )}

          {/* §32: Access — the former Session-settings drawer, one section among peers.
              key: its data ownership resets with the conversation, like the old row did. */}
          <AccessSection
            key={sessionId}
            sessionId={sessionId}
            personaId={personaId}
            projectScoped={projectScoped}
            workspace={workspace}
            branch={branch}
            scratchPrimary={scratchPrimary}
            openKey={openAccessKey}
            onOpenIntegrations={onOpenIntegrations}
          />
        </>
      )}
    </aside>
  );
}

function BrowserOperator({
  sessionId,
  refreshKey,
  running,
  toolNames,
  open,
  onToggle,
}: {
  sessionId: string;
  refreshKey: number;
  running: boolean;
  toolNames: string[];
  open: boolean;
  onToggle: () => void;
}) {
  const [state, setState] = useState<BrowserState | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewInterval, setPreviewInterval] = useState(3000);
  const [domainInput, setDomainInput] = useState("");
  const [selectedMediaId, setSelectedMediaId] = useState("");
  const [subtitleLanguage, setSubtitleLanguage] = useState<"" | "en" | "pt" | "es">("");
  const [downloadMessage, setDownloadMessage] = useState("");
  const [controlOpen, setControlOpen] = useState(false);
  const [controlAddress, setControlAddress] = useState("");
  const [controlText, setControlText] = useState("");
  const [controlError, setControlError] = useState("");
  const captureInFlight = useRef(false);
  const browserUsed = toolNames.some((name) => name.startsWith("browser_"));

  const refresh = () =>
    getBrowserState(sessionId)
      .then(setState)
      .catch(() => setState(null));

  useEffect(() => {
    refresh();
    if (!running && !state?.open) return;
    const timer = window.setInterval(refresh, 1500);
    return () => window.clearInterval(timer);
  }, [browserUsed, refreshKey, running, sessionId, state?.open]);

  useEffect(() => {
    const loadInterval = () =>
      getSettings()
        .then((settings) => setPreviewInterval(settings.browser_preview_interval_ms || 3000))
        .catch(() => setPreviewInterval(3000));
    const changed = (event: Event) => {
      const milliseconds = Number((event as CustomEvent).detail?.milliseconds);
      if (milliseconds) setPreviewInterval(milliseconds);
      else loadInterval();
    };
    loadInterval();
    window.addEventListener("coworker:browser-preview-settings-changed", changed);
    return () => window.removeEventListener("coworker:browser-preview-settings-changed", changed);
  }, []);

  useEffect(() => {
    if (!state?.open) return;
    const captureLivePreview = async () => {
      if (captureInFlight.current) return;
      captureInFlight.current = true;
      try {
        const next = await takeBrowserScreenshot(sessionId);
        setState(next);
      } catch {
        // Status polling remains active and will surface a controller error if present.
      } finally {
        captureInFlight.current = false;
      }
    };
    const timer = window.setInterval(captureLivePreview, previewInterval);
    return () => window.clearInterval(timer);
  }, [previewInterval, sessionId, state?.open]);

  const capture = async () => {
    setBusy(true);
    try {
      const next = await takeBrowserScreenshot(sessionId);
      setState(next);
    } finally {
      setBusy(false);
    }
  };
  const takeControl = async () => {
    setBusy(true);
    setControlError("");
    try {
      const result = await setBrowserControl(sessionId, "user");
      if (result.error) {
        setControlError(result.error);
        return;
      }
      const next = await takeBrowserScreenshot(sessionId);
      setState(next);
      setControlAddress(next.url || "");
      setControlOpen(true);
    } finally {
      setBusy(false);
    }
  };
  const returnControl = async () => {
    setBusy(true);
    setControlError("");
    try {
      const result = await setBrowserControl(sessionId, "agent");
      if (result.error) {
        setControlError(result.error);
        return;
      }
      setControlOpen(false);
      await refresh();
    } finally {
      setBusy(false);
    }
  };
  const humanAction = async (
    action: Parameters<typeof performBrowserHumanAction>[1],
  ) => {
    setBusy(true);
    setControlError("");
    try {
      const next = await performBrowserHumanAction(sessionId, action);
      if (next.error) {
        setControlError(next.error);
        return;
      }
      setState(next);
      setControlAddress(next.url || controlAddress);
    } finally {
      setBusy(false);
    }
  };
  const close = async () => {
    setBusy(true);
    try {
      await closeBrowser(sessionId);
      await refresh();
    } finally {
      setBusy(false);
    }
  };
  const updatePolicy = async (alwaysAllow: boolean, domains: string[]) => {
    setBusy(true);
    try {
      await setBrowserPolicy(sessionId, {
        always_allow_reads: alwaysAllow,
        allowed_domains: domains,
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  };
  const addDomain = async () => {
    const domain = domainInput.trim().toLowerCase();
    if (!domain) return;
    await updatePolicy(false, [...(state?.allowed_domains || []), domain]);
    setDomainInput("");
  };
  const directMedia = state?.media || [];
  const streamingMedia = state?.streaming_media || [];
  const mediaOptions = directMedia.length
    ? directMedia.map((item) => ({
        id: item.id,
        source: "direct" as const,
        label: `${item.kind === "video" ? "Video" : "Audio"} · ${item.resolution}${
          item.mime_type ? ` · ${item.mime_type.replace(/^(video|audio)\//, "")}` : ""
        }`,
      }))
    : streamingMedia.map((item) => ({
        id: item.id,
        source: "stream" as const,
        label: item.label + (item.filesize ? ` · ~${Math.ceil(item.filesize / 1024 / 1024)} MB` : ""),
      }));
  const selectedMediaOption =
    mediaOptions.find((item) => item.id === selectedMediaId) || mediaOptions[0];
  const analyzeStreamingMedia = async () => {
    setBusy(true);
    setDownloadMessage("Analyzing available formats…");
    try {
      const result = await analyzeBrowserStreamingMedia(sessionId);
      setDownloadMessage(result.ok ? "" : result.error || "No streaming formats were found.");
      setSelectedMediaId("");
      await refresh();
    } finally {
      setBusy(false);
    }
  };
  const downloadMedia = async () => {
    const option = mediaOptions.find((item) => item.id === selectedMediaId) || mediaOptions[0];
    if (!option) return;
    setBusy(true);
    setDownloadMessage("Downloading…");
    try {
      const result =
        option.source === "direct"
          ? await downloadBrowserMedia(sessionId, option.id)
          : await downloadBrowserStreamingMedia(
              sessionId,
              option.id,
              option.label.startsWith("Video") ? subtitleLanguage : "",
            );
      setDownloadMessage(
        result.ok
          ? `Saved to ${result.path}`
          : result.error || "The download could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  };
  const cancelMediaDownload = async () => {
    setDownloadMessage("Cancelling download…");
    const result = await cancelBrowserStreamingMedia(sessionId);
    if (!result.ok) {
      setDownloadMessage(result.error || "The download could not be cancelled.");
    }
    await refresh();
  };
  const mediaProgress = state?.streaming_media_progress || {};
  const progressPercent = Math.max(0, Math.min(100, mediaProgress.percent || 0));
  const formatBytes = (bytes?: number) => {
    if (!bytes) return "";
    if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    return `${Math.ceil(bytes / 1024)} KB`;
  };

  return (
    <>
    <RailSection
      title="Secure Browser"
      open={open}
      onToggle={onToggle}
      action={
        <button
          className="rail-mini-btn"
          onClick={(event) => {
            event.stopPropagation();
            refresh();
          }}
          title="Refresh browser status"
          aria-label="Refresh browser status"
        >
          <Icon name="refresh" size={13} />
        </button>
      }
    >
      <div className="browser-mini">
        <div className="browser-status-row">
          <span className={`browser-status-dot ${state?.status || "closed"}`} />
          <span>{state?.open ? "Isolated session active" : "Ready for this session"}</span>
        </div>
        {state?.url && (
          <div className="browser-location">
            <strong>{state.title || "Current page"}</strong>
            <span title={state.url}>{state.url}</span>
          </div>
        )}
        {state?.screenshot_data_url && (
          <>
            <div className="browser-shot-wrap">
              <img
                className="browser-shot"
                src={state.screenshot_data_url}
                alt={state.open ? "Current secure browser page" : "Last secure browser preview"}
              />
              {state.pending_action?.box &&
                state.pending_action?.viewport &&
                state.pending_action.status !== "stale" && (
                  <span
                    className="browser-target-overlay"
                    aria-hidden="true"
                    style={{
                      left: `${(state.pending_action.box.x / state.pending_action.viewport.width) * 100}%`,
                      top: `${(state.pending_action.box.y / state.pending_action.viewport.height) * 100}%`,
                      width: `${(state.pending_action.box.width / state.pending_action.viewport.width) * 100}%`,
                      height: `${(state.pending_action.box.height / state.pending_action.viewport.height) * 100}%`,
                    }}
                  >
                    1
                  </span>
                )}
            </div>
            {!state.open && <div className="rail-muted">Last browser preview</div>}
          </>
        )}
        {!!state?.pending_action?.tool_name && (
          <BrowserActionInspector action={state.pending_action} />
        )}
        {(state?.open || !!state?.media?.length) && (
          <div className="browser-media">
            <div className="browser-subhead">Page media</div>
            {!!mediaOptions.length ? (
              <>
                <div className="rail-muted">
                  Choose an available audio or video source and resolution.
                  Download only media you have permission to save.
                </div>
                <div className="browser-media-actions">
                  <select
                    value={selectedMediaId || mediaOptions[0].id}
                    onChange={(event) => {
                      setSelectedMediaId(event.target.value);
                      setDownloadMessage("");
                    }}
                    aria-label="Media format and resolution"
                  >
                    {mediaOptions.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                  {selectedMediaOption?.source === "stream" &&
                    selectedMediaOption.label.startsWith("Video") && (
                      <select
                        value={subtitleLanguage}
                        onChange={(event) =>
                          setSubtitleLanguage(event.target.value as "" | "en" | "pt" | "es")
                        }
                        aria-label="Embedded subtitle language"
                      >
                        <option value="">No subtitles</option>
                        <option value="en">English subtitles</option>
                        <option value="pt">Portuguese subtitles</option>
                        <option value="es">Spanish subtitles</option>
                      </select>
                    )}
                  <button className="btn secondary" onClick={downloadMedia} disabled={busy}>
                    Download
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="rail-muted">
                  No direct media file was detected. Analyze the page for YouTube,
                  HLS, DASH, and other supported streaming formats.
                </div>
                <button
                  className="btn secondary"
                  onClick={analyzeStreamingMedia}
                  disabled={busy}
                >
                  Analyze streaming formats
                </button>
              </>
            )}
            {downloadMessage && (
              <div
                className={
                  /^(Saved|Analyzing|Downloading)/.test(downloadMessage)
                    ? "rail-muted"
                    : "browser-error"
                }
              >
                {downloadMessage}
              </div>
            )}
            {(state?.streaming_media_status === "downloading" ||
              mediaProgress.stage === "completed") && (
              <div className="browser-download-progress" aria-live="polite">
                <div className="browser-download-progress-head">
                  <span>{mediaProgress.label || "Preparing download"}</span>
                  <strong>{progressPercent}%</strong>
                </div>
                <div
                  className="browser-download-progress-track"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={progressPercent}
                >
                  <span style={{ width: `${progressPercent}%` }} />
                </div>
                {mediaProgress.stage === "downloading" && (
                  <div className="browser-download-progress-meta">
                    <span>
                      {formatBytes(mediaProgress.downloaded_bytes)}
                      {mediaProgress.total_bytes
                        ? ` of ${formatBytes(mediaProgress.total_bytes)}`
                        : ""}
                    </span>
                    <span>
                      {mediaProgress.speed_bytes_per_second
                        ? `${formatBytes(mediaProgress.speed_bytes_per_second)}/s`
                        : ""}
                      {mediaProgress.eta_seconds
                        ? ` · ${mediaProgress.eta_seconds}s remaining`
                        : ""}
                    </span>
                  </div>
                )}
                {mediaProgress.translator && (
                  <div className="rail-muted">Translator: {mediaProgress.translator}</div>
                )}
                {state?.streaming_media_status === "downloading" &&
                  mediaProgress.stage !== "cancelling" && (
                    <button
                      className="btn secondary browser-download-cancel"
                      onClick={cancelMediaDownload}
                    >
                      Cancel download
                    </button>
                  )}
              </div>
            )}
          </div>
        )}
        {state?.last_error && <div className="browser-error">{state.last_error}</div>}
        <div className="rail-muted">
          This agent can navigate public pages in an isolated browser. Page content is
          untrusted; interactions require your approval. Live preview refreshes every {previewInterval} ms.
        </div>
        <div className="browser-permissions">
          <div className="browser-subhead">Navigation permissions</div>
          <label className="browser-read-toggle">
            <input
              type="checkbox"
              checked={state?.always_allow_reads ?? true}
              disabled={busy}
              onChange={(event) =>
                updatePolicy(event.target.checked, state?.allowed_domains || [])
              }
            />
            <span>Allow reads from any public domain for this session</span>
          </label>
          {!state?.always_allow_reads && (
            <>
              <div className="browser-domain-entry">
                <input
                  value={domainInput}
                  onChange={(event) => setDomainInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") addDomain();
                  }}
                  placeholder="example.com"
                  aria-label="Allowed browser domain"
                />
                <button className="btn secondary" onClick={addDomain} disabled={busy || !domainInput.trim()}>
                  Add
                </button>
              </div>
              <div className="browser-domain-list">
                {(state?.allowed_domains || []).map((domain) => (
                  <button
                    key={domain}
                    className="browser-domain-chip"
                    title={`Remove ${domain}`}
                    onClick={() =>
                      updatePolicy(
                        false,
                        (state?.allowed_domains || []).filter((item) => item !== domain),
                      )
                    }
                  >
                    {domain} ×
                  </button>
                ))}
                {!state?.allowed_domains?.length && (
                  <span className="rail-muted">No domains allowed yet.</span>
                )}
              </div>
            </>
          )}
        </div>
        {!!state?.history?.length && (
          <details className="browser-history">
            <summary>Navigation evidence ({state.history.length})</summary>
            <div className="browser-history-list">
              {state.history.slice(-5).reverse().map((item) => (
                <div key={`${item.visited_at}-${item.url}`} className="browser-history-item">
                  <strong>{item.title || "Untitled page"}</strong>
                  <span title={item.url}>{item.url}</span>
                  <time>{new Date(item.visited_at).toLocaleTimeString()}</time>
                </div>
              ))}
            </div>
          </details>
        )}
        {state?.open && (
          <div className="rail-actions">
            <button
              className="btn primary"
              onClick={() => {
                if (state.control_owner === "user") {
                  setControlAddress(state.url || "");
                  setControlOpen(true);
                } else {
                  takeControl();
                }
              }}
              disabled={busy || (state.control_owner !== "user" && !!state.pending_action?.tool_name)}
              title={
                state.pending_action?.tool_name
                  ? "Resolve the pending browser approval first"
                  : "Interact with this browser inside OpenWorker"
              }
            >
              {state.control_owner === "user" ? "Resume control" : "Take control"}
            </button>
            <button className="btn secondary" onClick={capture} disabled={busy}>
              Refresh preview
            </button>
            <button className="btn secondary" onClick={close} disabled={busy}>
              Close browser
            </button>
          </div>
        )}
      </div>
    </RailSection>
    {controlOpen && state?.open && (
      <div className="browser-control-backdrop" role="presentation">
        <section
          className="browser-control-modal"
          role="dialog"
          aria-modal="true"
          aria-label="Interactive Secure Browser"
        >
          <header className="browser-control-header">
            <div>
              <strong>Secure Browser</strong>
              <span><i /> You are in control</span>
            </div>
            <button className="btn primary" onClick={returnControl} disabled={busy}>
              Return to agent
            </button>
          </header>
          <div className="browser-control-toolbar">
            <button aria-label="Go back" title="Back" onClick={() => humanAction({ action: "back" })} disabled={busy}>←</button>
            <button aria-label="Go forward" title="Forward" onClick={() => humanAction({ action: "forward" })} disabled={busy}>→</button>
            <button aria-label="Reload page" title="Reload" onClick={() => humanAction({ action: "reload" })} disabled={busy}>↻</button>
            <input
              value={controlAddress}
              onChange={(event) => setControlAddress(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && controlAddress.trim()) {
                  humanAction({ action: "open_url", url: controlAddress.trim() });
                }
              }}
              aria-label="Browser address"
            />
            <button
              onClick={() => humanAction({ action: "open_url", url: controlAddress.trim() })}
              disabled={busy || !controlAddress.trim()}
            >
              Go
            </button>
          </div>
          <div className="browser-control-canvas">
            {state.screenshot_data_url ? (
              <img
                src={state.screenshot_data_url}
                alt="Interactive browser preview"
                onClick={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  humanAction({
                    action: "click",
                    x: ((event.clientX - bounds.left) / bounds.width) * 1280,
                    y: ((event.clientY - bounds.top) / bounds.height) * 900,
                  });
                }}
              />
            ) : (
              <div className="rail-muted">The live preview is not available yet.</div>
            )}
          </div>
          <div className="browser-control-inputs">
            <div className="browser-control-scroll">
              <button onClick={() => humanAction({ action: "scroll", delta_y: -650 })} disabled={busy}>Scroll up</button>
              <button onClick={() => humanAction({ action: "scroll", delta_y: 650 })} disabled={busy}>Scroll down</button>
            </div>
            <div className="browser-control-type">
              <input
                value={controlText}
                onChange={(event) => setControlText(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && controlText) {
                    humanAction({ action: "type", text: controlText });
                    setControlText("");
                  }
                }}
                placeholder="Click a field, then type here"
                aria-label="Text to type into the focused browser field"
              />
              <button
                onClick={() => {
                  humanAction({ action: "type", text: controlText });
                  setControlText("");
                }}
                disabled={busy || !controlText}
              >
                Type
              </button>
              <button onClick={() => humanAction({ action: "key", key: "Tab" })} disabled={busy}>Tab</button>
              <button onClick={() => humanAction({ action: "key", key: "Enter" })} disabled={busy}>Enter</button>
              <button onClick={() => humanAction({ action: "key", key: "Backspace" })} disabled={busy}>⌫</button>
            </div>
          </div>
          {controlError && <div className="browser-error">{controlError}</div>}
          <footer>
            Click the preview to focus or activate page elements. Your actions are applied
            to the same isolated session the agent uses.
          </footer>
        </section>
      </div>
    )}
    </>
  );
}

export function BrowserActionInspector({
  action,
}: {
  action: BrowserState["pending_action"];
}) {
  const status =
    action.status === "stale"
      ? "Target changed"
      : action.status === "approved"
        ? "Approved — verifying target"
        : "Approval required";
  return (
    <div className={`browser-action-inspector ${action.status || "pending"}`} aria-live="polite">
      <div className="browser-action-head">
        <span className="browser-action-number">1</span>
        <strong>{action.action || "Browser action"}</strong>
        <span>{status}</span>
      </div>
      <div className="browser-action-target">{action.label || action.target || "Page element"}</div>
      {action.content_summary && (
        <div className="browser-action-content">
          <Icon name="shield" size={13} />
          <span>{action.content_summary}</span>
        </div>
      )}
      <dl>
        <div><dt>Site</dt><dd>{action.domain || "Current page"}</dd></div>
        <div><dt>Risk</dt><dd>{action.risk || "Page interaction"}</dd></div>
        <div><dt>Expected</dt><dd>{action.expected_result || "The page changes as described."}</dd></div>
      </dl>
      {action.error && <div className="browser-error">{action.error}</div>}
      {action.status === "pending" && (
        <div className="rail-muted">Approve or deny this action in the composer.</div>
      )}
    </div>
  );
}

function ProgressSummary({ running, toolNames, todo }: { running: boolean; toolNames: string[]; todo: TodoItem[] }) {
  if (todo.length) {
    return (
      <div className="rail-todo-list">
        {todo.map((item, index) => (
          <div className={"rail-todo " + item.status} key={index}>
            <span className="rail-todo-mark" />
            <span>{item.content}</span>
          </div>
        ))}
        {running && (
          <div className="rail-muted">
            {toolNames.length ? `${toolNames.length} tool call${toolNames.length === 1 ? "" : "s"} so far.` : "Working..."}
          </div>
        )}
      </div>
    );
  }
  if (running) {
    return (
      <div className="rail-muted">
        Working on this task{toolNames.length ? ` with ${toolNames.length} tool call${toolNames.length === 1 ? "" : "s"} so far.` : "."}
      </div>
    );
  }
  return (
    <div className="rail-muted">
      For longer multi-step tasks, progress will appear here while OpenWorker plans, uses tools, waits for approval, and produces artifacts.
    </div>
  );
}

function RailSection({
  title,
  open,
  onToggle,
  children,
  action,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="rail-section">
      <div className="rail-section-head">
        <button className="rail-section-toggle" onClick={onToggle}>
          <Icon name={open ? "chevronDown" : "chevronRight"} size={14} className="rail-chev" />
          <span>{title}</span>
        </button>
        {action}
      </div>
      {open && <div className="rail-section-body">{children}</div>}
    </section>
  );
}

function ArtifactViewer({
  sessionId,
  artifact,
  content,
  onReload,
  onBack,
}: {
  sessionId: string;
  artifact: ArtifactInfo;
  content: ArtifactContent | null;
  onReload: () => Promise<void>;
  onBack: () => void;
}) {
  const [reloadKey, setReloadKey] = useState(0);
  const isHtml = content?.kind === "html" && !content.error;
  // Best viewed in a real app: spreadsheets, PDFs, and Office docs (pptx/docx can't preview inline)
  const isApp = content?.kind === "sheet" || content?.kind === "pdf" || content?.kind === "office";

  return (
    <div className="artifact-viewer">
      <div className="artifact-head">
        <button className="artifact-icon-btn" onClick={onBack} aria-label="Back to artifacts" title="Back">
          <Icon name="arrowLeft" size={16} />
        </button>
        <div className="artifact-heading">
          <div className="artifact-title"><span>Artifacts</span><span className="artifact-sep">/</span><span>{artifact.name}</span></div>
          <div className="artifact-path">{artifact.path}</div>
        </div>
        <div className="rail-actions">
          {isHtml && (
            <button
              className="artifact-icon-btn"
              onClick={async () => {
                await onReload();
                setReloadKey((k) => k + 1);
              }}
              aria-label="Reload preview"
              title="Reload"
            >
              <Icon name="refresh" size={16} />
            </button>
          )}
          {isApp && (
            <button
              className="artifact-icon-btn"
              onClick={() => revealArtifact(sessionId, artifact.path, "open")}
              aria-label="Open in default app"
              title="Open in default app"
            >
              <Icon name="panelOpen" size={16} />
            </button>
          )}
          {/* Copy the ABSOLUTE path — the workspace-relative one is useless outside the app
              (tester catch 2026-07-12: it copied just "slack-connector-debug.md"). */}
          <button
            className="artifact-icon-btn"
            onClick={() => navigator.clipboard?.writeText(artifact.abs_path || artifact.path)}
            aria-label="Copy path"
            title="Copy full path"
          >
            <Icon name="copy" size={16} />
          </button>
          <button
            className="artifact-icon-btn"
            onClick={() => revealArtifact(sessionId, artifact.path, "reveal")}
            aria-label="Show in folder"
            title="Show in folder"
          >
            <Icon name="folder" size={16} />
          </button>
        </div>
      </div>
      <div className="artifact-preview">
        {!content ? (
          <div className="rail-muted">Loading...</div>
        ) : content.error ? (
          <div className="rail-error">{content.error}</div>
        ) : content.kind === "html" ? (
          <iframe
            key={`${artifact.path}-${reloadKey}`}
            sandbox="allow-scripts allow-same-origin"
            className="artifact-frame"
            srcDoc={content.content || ""}
          />
        ) : content.kind === "markdown" ? (
          <div className="artifact-md">
            <Markdown text={content.content || ""} />
          </div>
        ) : content.kind === "image" ? (
          <img className="artifact-image" src={content.data_url} />
        ) : content.kind === "pdf" ? (
          <PdfViewer dataUrl={content.data_url || ""} />
        ) : content.kind === "csv" ? (
          <CsvTable text={content.content || ""} />
        ) : content.kind === "sheet" ? (
          <SheetViewer dataUrl={content.data_url || ""} />
        ) : content.kind === "office" ? (
          <div className="artifact-open-prompt">
            <Icon name="panelOpen" size={28} />
            <p>This {/\.pptx?$/i.test(artifact.name) ? "PowerPoint" : "Word"} file can’t be previewed here.</p>
            <button className="btn sm" onClick={() => revealArtifact(sessionId, artifact.path, "open")}>
              Open in default app
            </button>
          </div>
        ) : (
          <pre className="artifact-code">{content.content}</pre>
        )}
      </div>
    </div>
  );
}

const MAX_TABLE_ROWS = 500;

function GridTable({ rows, note }: { rows: unknown[][]; note?: string }) {
  const [head, ...body] = rows;
  return (
    <div className="artifact-tablewrap">
      <table className="artifact-table">
        {head && (
          <thead>
            <tr>{head.map((c, i) => <th key={i}>{String(c ?? "")}</th>)}</tr>
          </thead>
        )}
        <tbody>
          {body.slice(0, MAX_TABLE_ROWS).map((r, i) => (
            <tr key={i}>{r.map((c, j) => <td key={j}>{String(c ?? "")}</td>)}</tr>
          ))}
        </tbody>
      </table>
      {(note || body.length > MAX_TABLE_ROWS) && (
        <div className="rail-muted artifact-table-note">
          {note}
          {body.length > MAX_TABLE_ROWS ? ` Showing first ${MAX_TABLE_ROWS} of ${body.length} rows.` : ""}
        </div>
      )}
    </div>
  );
}

// Minimal RFC-4180-ish CSV parsing: quoted fields, escaped quotes, CRLF. TSV via tab sniffing.
function parseCsv(text: string): string[][] {
  const delim = text.includes("\t") && !text.split("\n")[0]?.includes(",") ? "\t" : ",";
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i++;
        } else quoted = false;
      } else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === delim) {
      row.push(cell);
      cell = "";
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      cell = "";
      rows.push(row);
      row = [];
    } else cell += ch;
  }
  if (cell !== "" || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows.filter((r) => r.some((c) => c !== ""));
}

function CsvTable({ text }: { text: string }) {
  const rows = parseCsv(text);
  if (!rows.length) return <div className="rail-muted artifact-table-note">Empty file.</div>;
  return <GridTable rows={rows} />;
}

// xlsx/xls preview via SheetJS (loaded on demand — it's a heavy module): sheet tabs + a capped
// grid. Real spreadsheet work belongs in Numbers/Excel via "Open in default app".
// WKWebView has no inline PDF plugin (<embed> shows a gray pane in the Tauri shell), so we
// rasterize pages with pdf.js onto stacked canvases — same lazy-chunk pattern as SheetViewer.
function PdfViewer({ dataUrl }: { dataUrl: string }) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const holder = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError("");
    setLoading(true);
    const base64 = dataUrl.split(",")[1] || "";
    import("pdfjs-dist")
      .then(async (pdfjs) => {
        pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;
        const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
        const doc = await pdfjs.getDocument({ data: bytes }).promise;
        const el = holder.current;
        if (cancelled || !el) return;
        el.innerHTML = "";
        const width = el.clientWidth || 640;
        const dpr = window.devicePixelRatio || 1;
        for (let i = 1; i <= doc.numPages; i++) {
          const page = await doc.getPage(i);
          const base = page.getViewport({ scale: 1 });
          const viewport = page.getViewport({ scale: (width / base.width) * dpr });
          const canvas = document.createElement("canvas");
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.className = "artifact-pdf-page";
          await page.render({ canvasContext: canvas.getContext("2d")!, viewport }).promise;
          if (cancelled) return;
          el.appendChild(canvas);
        }
        setLoading(false);
      })
      .catch((e) => !cancelled && setError(String(e?.message || e)));
    return () => {
      cancelled = true;
    };
  }, [dataUrl]);

  if (error) return <div className="rail-error artifact-table-note">Could not render PDF: {error}</div>;
  return (
    <div className="artifact-pdfjs">
      {loading && <div className="rail-muted artifact-table-note">Rendering PDF…</div>}
      <div ref={holder} />
    </div>
  );
}

function SheetViewer({ dataUrl }: { dataUrl: string }) {
  const [sheets, setSheets] = useState<{ name: string; rows: unknown[][] }[] | null>(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setSheets(null);
    setError("");
    setActive(0);
    const base64 = dataUrl.split(",")[1] || "";
    import("xlsx")
      .then((XLSX) => {
        if (cancelled) return;
        const wb = XLSX.read(base64, { type: "base64" });
        setSheets(
          wb.SheetNames.map((name) => ({
            name,
            rows: XLSX.utils.sheet_to_json(wb.Sheets[name], { header: 1, defval: "" }) as unknown[][],
          })),
        );
      })
      .catch((e) => !cancelled && setError(String(e?.message || e)));
    return () => {
      cancelled = true;
    };
  }, [dataUrl]);

  if (error) return <div className="rail-error artifact-table-note">Could not parse spreadsheet: {error}</div>;
  if (!sheets) return <div className="rail-muted artifact-table-note">Parsing spreadsheet…</div>;
  const sheet = sheets[active];
  return (
    <div className="sheet-viewer">
      {sheets.length > 1 && (
        <div className="sheet-tabs">
          {sheets.map((s, i) => (
            <button key={s.name} className={"sheet-tab" + (i === active ? " active" : "")} onClick={() => setActive(i)}>
              {s.name}
            </button>
          ))}
        </div>
      )}
      {sheet.rows.length ? <GridTable rows={sheet.rows} /> : <div className="rail-muted artifact-table-note">Empty sheet.</div>}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(epochSeconds: number): string {
  if (!epochSeconds) return "";
  return new Date(epochSeconds * 1000).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}
