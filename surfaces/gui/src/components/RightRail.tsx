import { useEffect, useRef, useState, type ReactNode } from "react";
// Emits the asset URL only; the worker itself loads lazily with the pdfjs chunk.
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import {
  closeBrowser,
  downloadBrowserMedia,
  getArtifacts,
  getBrowserState,
  getSettings,
  readArtifact,
  revealArtifact,
  setBrowserPolicy,
  takeBrowserScreenshot,
  type ArtifactContent,
  type ArtifactInfo,
  type BrowserState,
} from "../api";
import type { TodoItem } from "../types";
import { AccessSection } from "./AccessSection";
import { Icon } from "./Icon";
import { Markdown, OPEN_ARTIFACT_EVENT } from "./Markdown";

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
}: Props) {
  const [open, setOpen] = useState<Record<Panel, boolean>>({
    progress: true,
    browser: true,
    artifacts: true,
  });
  const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
  const [selected, setSelected] = useState<ArtifactInfo | null>(null);
  const [content, setContent] = useState<ArtifactContent | null>(null);

  const refreshArtifacts = () => getArtifacts(sessionId).then(setArtifacts).catch(() => setArtifacts([]));

  useEffect(() => {
    if (!active) return;
    if (showArtifacts) refreshArtifacts();
  }, [active, sessionId, refreshKey, showArtifacts]);

  // Switching conversations closes any open artifact — it belongs to the previous session's
  // workspace, which the new session can't (and shouldn't) read.
  useEffect(() => {
    setSelected(null);
    setContent(null);
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
  const [downloadMessage, setDownloadMessage] = useState("");
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
  const downloadMedia = async () => {
    const mediaId = selectedMediaId || state?.media?.[0]?.id;
    if (!mediaId) return;
    setBusy(true);
    setDownloadMessage("Downloading…");
    try {
      const result = await downloadBrowserMedia(sessionId, mediaId);
      setDownloadMessage(
        result.ok
          ? `Saved to ${result.path}`
          : result.error || "The download could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
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
            <img
              className="browser-shot"
              src={state.screenshot_data_url}
              alt={state.open ? "Current secure browser page" : "Last secure browser preview"}
            />
            {!state.open && <div className="rail-muted">Last browser preview</div>}
          </>
        )}
        {(state?.open || !!state?.media?.length) && (
          <div className="browser-media">
            <div className="browser-subhead">Page media</div>
            {!!state?.media?.length ? (
              <>
                <div className="rail-muted">
                  Choose an available audio or video source and resolution.
                </div>
                <div className="browser-media-actions">
                  <select
                    value={selectedMediaId || state.media[0].id}
                    onChange={(event) => {
                      setSelectedMediaId(event.target.value);
                      setDownloadMessage("");
                    }}
                    aria-label="Media format and resolution"
                  >
                    {state.media.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.kind === "video" ? "Video" : "Audio"} · {item.resolution}
                        {item.mime_type ? ` · ${item.mime_type.replace(/^(video|audio)\//, "")}` : ""}
                      </option>
                    ))}
                  </select>
                  <button className="btn secondary" onClick={downloadMedia} disabled={busy}>
                    Download
                  </button>
                </div>
              </>
            ) : (
              <div className="rail-muted">
                No direct downloadable media was detected. The page may be using a
                protected or streaming source.
              </div>
            )}
            {downloadMessage && (
              <div className={downloadMessage.startsWith("Saved") ? "rail-muted" : "browser-error"}>
                {downloadMessage}
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
