import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { ArtifactInfo } from "../api";
import { Icon } from "./Icon";

export function buildMarkdownPdfPrompt(path: string): string {
  return `Convert this existing Markdown artifact to a polished PDF:

Source: ${path}

Requirements:
- Read the source from the current session workspace and never modify or overwrite it.
- Write the PDF beside the source using the same base filename and a .pdf extension.
- Preserve headings, paragraphs, lists, tables, blockquotes, code blocks, links, and local images where possible.
- Use a local open-source renderer. Prefer Pandoc with WeasyPrint when safely available; otherwise use a sanitized HTML render through the bundled Playwright Chromium PDF printer.
- Treat Markdown and embedded HTML as untrusted content. Do not execute scripts, load local files outside the workspace, or fetch remote assets without approval.
- Apply professional print typography, margins, page breaks, code wrapping, page numbers, and readable link styling.
- Reopen the generated PDF, verify page count and extractable text, render every page to images, and fix clipping, broken tables, missing glyphs, or unreadable content.
- End with a clickable artifact link to the PDF.`;
}

export function MarkdownPdfLauncher({
  artifacts,
  onCreate,
}: {
  artifacts: ArtifactInfo[];
  onCreate: (prompt: string) => void;
}) {
  const markdown = artifacts.filter((artifact) =>
    /\.(md|markdown)$/i.test(artifact.path),
  );
  const [open, setOpen] = useState(false);
  const [path, setPath] = useState("");

  useEffect(() => {
    if (!markdown.some((artifact) => artifact.path === path)) {
      setPath(markdown[0]?.path || "");
    }
  }, [artifacts, markdown, path]);

  if (!markdown.length) return null;

  const close = () => setOpen(false);
  return (
    <>
      <button className="research-launch-button" onClick={() => setOpen(true)}>
        <Icon name="file" size={15} />
        <span>Markdown to PDF</span>
      </button>
      {open &&
        createPortal(
          <div className="research-modal-backdrop" onMouseDown={close}>
            <section
              className="research-modal markdown-pdf-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="markdown-pdf-title"
              onMouseDown={(event) => event.stopPropagation()}
            >
              <header className="research-modal-header">
                <div>
                  <span className="research-modal-eyebrow">Artifact Studio</span>
                  <h2 id="markdown-pdf-title">Markdown to PDF</h2>
                  <p>Create a print-ready PDF without changing the source file.</p>
                </div>
                <button className="artifact-icon-btn" onClick={close} aria-label="Close">
                  <Icon name="x" size={17} />
                </button>
              </header>
              <label className="research-field">
                <span>Markdown artifact</span>
                <select
                  aria-label="Markdown artifact"
                  value={path}
                  onChange={(event) => setPath(event.target.value)}
                >
                  {markdown.map((artifact) => (
                    <option key={artifact.path} value={artifact.path}>
                      {artifact.path}
                    </option>
                  ))}
                </select>
              </label>
              <footer className="research-modal-actions">
                <button className="btn" onClick={close}>Cancel</button>
                <button
                  className="btn primary"
                  disabled={!path}
                  onClick={() => {
                    onCreate(buildMarkdownPdfPrompt(path));
                    close();
                  }}
                >
                  Review in composer
                </button>
              </footer>
            </section>
          </div>,
          document.body,
        )}
    </>
  );
}
