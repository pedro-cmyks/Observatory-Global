#!/usr/bin/env python3
"""Serve a local one-row-at-a-time Atlas adjudication UI."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from scripts.atlas_label_workflow import (
        VALID_DECISIONS,
        VALID_ERROR_TYPES,
        VALID_EVIDENCE_ROLES,
        VALID_SCOPES,
        VALID_SUPPORTED_QUESTIONS,
        read_jsonl,
        review_template_progress,
        write_jsonl,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from atlas_label_workflow import (
        VALID_DECISIONS,
        VALID_ERROR_TYPES,
        VALID_EVIDENCE_ROLES,
        VALID_SCOPES,
        VALID_SUPPORTED_QUESTIONS,
        read_jsonl,
        review_template_progress,
        write_jsonl,
    )


ORDERED_DECISIONS = ["correct", "incorrect", "unclear"]
ORDERED_SCOPES = [
    "child_thread",
    "evidence",
    "parent_thread",
    "entity_thread",
    "context_signal",
    "domain",
    "geo_context",
    "source_context",
    "noise",
]
ORDERED_EVIDENCE_ROLES = [
    "primary_event",
    "followup",
    "reaction",
    "analysis",
    "background",
    "public_attention",
    "source_amplification",
    "not_evidence",
]
ORDERED_ERROR_TYPES = [
    "off_topic",
    "substring_noise",
    "scope_mismatch",
    "parent_thread_candidate",
    "primary_context_mismatch",
    "insufficient_context",
]
ORDERED_QUESTIONS = [
    "why_moving",
    "what_changed",
    "where_concentrated",
    "subthreads_forming",
    "sources_driving",
    "evidence_support",
    "related_thread",
]

ALLOWED_UPDATE_FIELDS = {
    "accept_assistant_label",
    "reviewer_decision",
    "reviewer_scope",
    "reviewer_evidence_role",
    "reviewer_error_type",
    "reviewer_parent_thread",
    "reviewer_child_thread",
    "reviewer_supported_questions",
    "reviewer_notes",
}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validate_optional(value: Any, valid_values: set[str], field: str) -> str | None:
    if value is None or value == "":
        return None
    if value not in valid_values:
        raise ValueError(f"Invalid {field}: {value!r}")
    return str(value)


def _validate_questions(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("reviewer_supported_questions must be a list")
    questions: list[str] = []
    for question in value:
        if question not in VALID_SUPPORTED_QUESTIONS:
            raise ValueError(f"Invalid reviewer_supported_questions value: {question!r}")
        questions.append(str(question))
    return questions


def normalize_update(payload: dict[str, Any]) -> dict[str, Any]:
    update: dict[str, Any] = {}
    for field, value in payload.items():
        if field not in ALLOWED_UPDATE_FIELDS:
            continue
        if field == "accept_assistant_label":
            update[field] = value if isinstance(value, bool) else None
        elif field == "reviewer_decision":
            update[field] = _validate_optional(value, VALID_DECISIONS, field)
        elif field == "reviewer_scope":
            update[field] = _validate_optional(value, VALID_SCOPES, field)
        elif field == "reviewer_evidence_role":
            update[field] = _validate_optional(value, VALID_EVIDENCE_ROLES, field)
        elif field == "reviewer_error_type":
            update[field] = _validate_optional(value, VALID_ERROR_TYPES, field)
        elif field == "reviewer_supported_questions":
            update[field] = _validate_questions(value)
        else:
            update[field] = _clean_text(value)
    return update


def load_review_state(template_path: Path) -> dict[str, Any]:
    return {
        "template": str(template_path),
        "rows": read_jsonl(template_path),
        "progress": review_template_progress([template_path]),
        "options": {
            "decisions": ORDERED_DECISIONS,
            "scopes": ORDERED_SCOPES,
            "evidence_roles": ORDERED_EVIDENCE_ROLES,
            "error_types": ORDERED_ERROR_TYPES,
            "questions": ORDERED_QUESTIONS,
        },
    }


def update_review_row(template_path: Path, signal_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    rows = read_jsonl(template_path)
    update = normalize_update(payload)
    found = False
    for row in rows:
        if row.get("signal_id") == signal_id:
            row.update(update)
            found = True
            break
    if not found:
        raise KeyError(f"signal_id not found: {signal_id}")
    write_jsonl(template_path, rows)
    return load_review_state(template_path)


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Atlas Review</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #071016;
      --panel: #0d1823;
      --panel-2: #101f2e;
      --line: #244154;
      --text: #dbe8f2;
      --muted: #8aa2b3;
      --accent: #64f0bc;
      --warn: #f1bf5b;
      --bad: #ff6d7a;
      --blue: #75aaff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 3;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(7, 16, 22, 0.96);
    }
    h1 {
      margin: 0;
      font-size: 13px;
      letter-spacing: 0;
      color: var(--accent);
      text-transform: uppercase;
    }
    .status { color: var(--muted); font-variant-numeric: tabular-nums; }
    .shell {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 320px;
      gap: 16px;
      max-width: 1280px;
      margin: 0 auto;
      padding: 18px;
    }
    main, aside {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
    }
    main { min-height: calc(100vh - 92px); }
    .section { padding: 18px; border-bottom: 1px solid rgba(36, 65, 84, 0.7); }
    .headline { font-size: 24px; line-height: 1.18; margin: 8px 0 12px; }
    .meta { display: flex; flex-wrap: wrap; gap: 6px; }
    .chip {
      border: 1px solid rgba(117, 170, 255, 0.35);
      background: rgba(117, 170, 255, 0.1);
      color: #bdd5ff;
      border-radius: 4px;
      padding: 3px 6px;
      font-size: 12px;
    }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .group { margin-bottom: 16px; }
    .group h2 {
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .buttons { display: flex; flex-wrap: wrap; gap: 8px; }
    button {
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 6px;
      padding: 8px 10px;
      cursor: pointer;
      font: inherit;
    }
    button:hover { border-color: var(--accent); }
    button.selected {
      border-color: var(--accent);
      background: rgba(100, 240, 188, 0.14);
      color: var(--accent);
    }
    button.danger.selected {
      border-color: var(--bad);
      color: var(--bad);
      background: rgba(255, 109, 122, 0.1);
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      background: #08141f;
      color: var(--text);
      border-radius: 6px;
      padding: 10px;
      font: inherit;
    }
    textarea { min-height: 86px; resize: vertical; }
    label.check {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      margin: 0 8px 8px 0;
      padding: 7px 9px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-2);
      cursor: pointer;
    }
    .actions {
      position: sticky;
      bottom: 0;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 18px;
      background: rgba(13, 24, 35, 0.96);
      border-top: 1px solid var(--line);
      border-radius: 0 0 8px 8px;
    }
    .primary { background: rgba(100, 240, 188, 0.16); color: var(--accent); border-color: var(--accent); }
    .assistant {
      border-left: 3px solid var(--blue);
      background: rgba(117, 170, 255, 0.08);
      padding: 12px;
      border-radius: 6px;
      color: #cfe0ff;
    }
    .assistant ul { margin: 8px 0 0; padding-left: 18px; }
    .evidence { color: var(--muted); }
    aside { padding: 14px; align-self: start; position: sticky; top: 66px; }
    .row-list { display: grid; grid-template-columns: repeat(8, 1fr); gap: 6px; margin-top: 12px; }
    .row-dot {
      padding: 7px 0;
      text-align: center;
      border-radius: 5px;
      color: var(--muted);
    }
    .row-dot.ready { color: var(--accent); border-color: rgba(100,240,188,.6); }
    .row-dot.current { outline: 2px solid var(--blue); color: var(--text); }
    .muted { color: var(--muted); }
    @media (max-width: 880px) {
      .shell { grid-template-columns: 1fr; padding: 10px; }
      aside { position: static; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Atlas Review</h1>
    <div class="status" id="status">Loading...</div>
  </header>
  <div class="shell">
    <main>
      <div class="section">
        <div class="muted" id="counter"></div>
        <div class="headline" id="headline"></div>
        <div class="meta" id="meta"></div>
      </div>
      <div class="section">
        <div class="group">
          <h2>Evidence</h2>
          <div class="evidence" id="evidence"></div>
        </div>
        <div class="assistant" id="assistant"></div>
      </div>
      <div class="section">
        <div class="grid">
          <div class="group">
            <h2>Accept Suggestion</h2>
            <div class="buttons" data-field="accept_assistant_label"></div>
          </div>
          <div class="group">
            <h2>Decision</h2>
            <div class="buttons" data-field="reviewer_decision"></div>
          </div>
          <div class="group">
            <h2>Scope</h2>
            <div class="buttons" data-field="reviewer_scope"></div>
          </div>
          <div class="group">
            <h2>Evidence Role</h2>
            <div class="buttons" data-field="reviewer_evidence_role"></div>
          </div>
          <div class="group">
            <h2>Error Type</h2>
            <div class="buttons" data-field="reviewer_error_type"></div>
          </div>
          <div class="group">
            <h2>Supported Questions</h2>
            <div id="questions"></div>
          </div>
        </div>
        <div class="grid">
          <div class="group">
            <h2>Parent Thread</h2>
            <input id="reviewer_parent_thread" placeholder="e.g. corruption-watchdog-integrity" />
          </div>
          <div class="group">
            <h2>Child Thread</h2>
            <input id="reviewer_child_thread" placeholder="e.g. australian-watchdog-resignation" />
          </div>
        </div>
        <div class="group">
          <h2>Notes</h2>
          <textarea id="reviewer_notes" placeholder="Short evidence-based note"></textarea>
        </div>
      </div>
      <div class="actions">
        <div class="buttons">
          <button id="prev">Previous</button>
          <button id="next">Next</button>
        </div>
        <div class="buttons">
          <button id="save">Save</button>
          <button class="primary" id="saveNext">Save & Next</button>
        </div>
      </div>
    </main>
    <aside>
      <div class="muted">Progress</div>
      <div id="progress"></div>
      <div class="row-list" id="rowList"></div>
    </aside>
  </div>
<script>
let state = null;
let index = 0;
let draft = {};

const optionLabels = {
  correct: "Correct",
  incorrect: "Incorrect",
  unclear: "Unclear",
  child_thread: "Child thread",
  evidence: "Evidence",
  parent_thread: "Parent thread",
  entity_thread: "Entity thread",
  context_signal: "Context signal",
  domain: "Domain",
  geo_context: "Geo context",
  source_context: "Source context",
  noise: "Noise",
  primary_event: "Primary event",
  followup: "Follow-up",
  reaction: "Reaction",
  analysis: "Analysis",
  background: "Background",
  public_attention: "Public attention",
  source_amplification: "Source amplification",
  not_evidence: "Not evidence",
  off_topic: "Off topic",
  substring_noise: "Substring noise",
  scope_mismatch: "Scope mismatch",
  parent_thread_candidate: "Parent candidate",
  primary_context_mismatch: "Primary context mismatch",
  insufficient_context: "Insufficient context",
  why_moving: "Why moving",
  what_changed: "What changed",
  where_concentrated: "Where concentrated",
  subthreads_forming: "Subthreads forming",
  sources_driving: "Sources driving",
  evidence_support: "Evidence support",
  related_thread: "Related thread"
};

function label(value) {
  return optionLabels[value] || String(value || "None");
}

function isReady(row) {
  return row.accept_assistant_label === true || !!row.reviewer_decision;
}

async function fetchState() {
  const res = await fetch("/api/state");
  state = await res.json();
  const pending = state.rows.findIndex(row => !isReady(row));
  index = pending >= 0 ? pending : 0;
  render();
}

function row() { return state.rows[index]; }

function setField(field, value) {
  draft[field] = value;
  renderControls();
}

function valueFor(field) {
  return Object.prototype.hasOwnProperty.call(draft, field) ? draft[field] : row()[field];
}

function renderButtonGroup(field, values, danger = false) {
  const el = document.querySelector(`[data-field="${field}"]`);
  el.innerHTML = "";
  const none = document.createElement("button");
  none.textContent = "None";
  none.className = valueFor(field) == null ? "selected" : "";
  none.onclick = () => setField(field, null);
  el.appendChild(none);
  for (const value of values) {
    const button = document.createElement("button");
    button.textContent = label(value);
    button.className = (valueFor(field) === value ? "selected " : "") + (danger ? "danger" : "");
    button.onclick = () => setField(field, value);
    el.appendChild(button);
  }
}

function renderAcceptGroup() {
  const el = document.querySelector('[data-field="accept_assistant_label"]');
  el.innerHTML = "";
  for (const [text, value] of [["Unset", null], ["Accept", true], ["Manual", false]]) {
    const button = document.createElement("button");
    button.textContent = text;
    button.className = valueFor("accept_assistant_label") === value ? "selected" : "";
    button.onclick = () => setField("accept_assistant_label", value);
    el.appendChild(button);
  }
}

function renderQuestions() {
  const el = document.getElementById("questions");
  const selected = new Set(valueFor("reviewer_supported_questions") || []);
  el.innerHTML = "";
  for (const question of state.options.questions) {
    const wrapper = document.createElement("label");
    wrapper.className = "check";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = selected.has(question);
    input.onchange = () => {
      if (input.checked) selected.add(question); else selected.delete(question);
      draft.reviewer_supported_questions = [...selected];
      renderQuestions();
    };
    wrapper.appendChild(input);
    wrapper.appendChild(document.createTextNode(label(question)));
    el.appendChild(wrapper);
  }
}

function renderControls() {
  renderAcceptGroup();
  renderButtonGroup("reviewer_decision", state.options.decisions);
  renderButtonGroup("reviewer_scope", state.options.scopes);
  renderButtonGroup("reviewer_evidence_role", state.options.evidence_roles);
  renderButtonGroup("reviewer_error_type", state.options.error_types, true);
  renderQuestions();
  for (const field of ["reviewer_parent_thread", "reviewer_child_thread", "reviewer_notes"]) {
    document.getElementById(field).value = valueFor(field) || "";
  }
}

function render() {
  if (!state) return;
  draft = {};
  const current = row();
  document.getElementById("status").textContent =
    `${state.progress.ready_rows}/${state.progress.total_rows} ready`;
  document.getElementById("counter").textContent =
    `Signal ${index + 1} of ${state.rows.length} · ${current.signal_id}`;
  document.getElementById("headline").innerHTML = current.headline || "(no headline)";
  document.getElementById("meta").innerHTML = [
    current.assigned_topic_label,
    current.assigned_topic_slug,
    current.country_code,
    current.source_name,
    current.sample_bucket,
    `confidence ${current.confidence}`
  ].filter(Boolean).map(v => `<span class="chip">${v}</span>`).join("");
  const evidence = current.evidence || {};
  document.getElementById("evidence").textContent =
    `matched_terms=${JSON.stringify(evidence.matched_terms || [])}; lex=${evidence.lex_count ?? "-"}; theme=${evidence.theme_hits ?? "-"}; hint=${evidence.hint_count ?? "-"}`;
  document.getElementById("assistant").innerHTML = current.assistant_decision
    ? `<strong>Assistant suggestion</strong><ul>
        <li>decision: ${current.assistant_decision}</li>
        <li>scope: ${current.assistant_scope || "-"}</li>
        <li>role: ${current.assistant_evidence_role || "-"}</li>
        <li>parent: ${current.assistant_parent_thread || "-"}</li>
        <li>child: ${current.assistant_child_thread || "-"}</li>
        <li>questions: ${(current.assistant_supported_questions || []).join(", ") || "-"}</li>
      </ul>`
    : `<strong>No assistant suggestion</strong><div class="muted">Review directly from the evidence.</div>`;
  document.getElementById("progress").textContent =
    `${state.progress.ready_rows} ready · ${state.progress.remaining_rows} remaining`;
  const rowList = document.getElementById("rowList");
  rowList.innerHTML = "";
  state.rows.forEach((r, i) => {
    const button = document.createElement("button");
    button.textContent = i + 1;
    button.className = `row-dot ${isReady(r) ? "ready" : ""} ${i === index ? "current" : ""}`;
    button.onclick = () => { index = i; render(); };
    rowList.appendChild(button);
  });
  renderControls();
}

function collectPayload() {
  for (const field of ["reviewer_parent_thread", "reviewer_child_thread", "reviewer_notes"]) {
    draft[field] = document.getElementById(field).value.trim() || null;
  }
  return draft;
}

async function save() {
  const current = row();
  const res = await fetch(`/api/row/${current.signal_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectPayload())
  });
  state = await res.json();
}

document.getElementById("prev").onclick = () => { index = Math.max(0, index - 1); render(); };
document.getElementById("next").onclick = () => { index = Math.min(state.rows.length - 1, index + 1); render(); };
document.getElementById("save").onclick = async () => { await save(); render(); };
document.getElementById("saveNext").onclick = async () => {
  await save();
  const pending = state.rows.findIndex((r, i) => i > index && !isReady(r));
  index = pending >= 0 ? pending : Math.min(state.rows.length - 1, index + 1);
  render();
};
document.addEventListener("keydown", async (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    await document.getElementById("saveNext").click();
  }
});
fetchState();
</script>
</body>
</html>
"""


class ReviewHandler(BaseHTTPRequestHandler):
    template_path: Path

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        body = INDEX_HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send_html()
            return
        if path == "/api/state":
            self._send_json(load_review_state(self.template_path))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not path.startswith("/api/row/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            signal_id = int(path.rsplit("/", 1)[-1])
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            self._send_json(update_review_row(self.template_path, signal_id, payload))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[atlas-review] {self.address_string()} - {format % args}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve Atlas local review UI")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.template.exists():
        raise SystemExit(f"template does not exist: {args.template}")
    ReviewHandler.template_path = args.template
    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    print(f"Atlas review UI: http://{args.host}:{args.port}")
    print(f"Template: {args.template}")
    server.serve_forever()


if __name__ == "__main__":
    main()
