#!/usr/bin/env node
// Evidence-typing safety check for user-facing frontend rendering.
//
// DG-104 re-scope (David's ruling, 2026-08-29, recorded verbatim in
// ~/dg-build/DG091-DESIGN-BRIEF.md and DG-094): the frontend speaks plain
// fantasy-football prose and MAY state overall recommendations. The old
// presentation-language gates this scanner carried — banned_phrase and
// banned_standalone_word over visible UI text and CSS content — enforced the
// repealed no-recommendation law and are REMOVED under that authority.
//
// What SURVIVES is the evidence-typing half, which is measurement law and not
// presentation: rendering a typed decision FIELD (verdict / dynasty_tier /
// confidence / recommended_action / roster_action) exposes machinery the
// backend contract does not carry and must not grow. Two gates stay armed:
//   banned_field_render - terminal property name rendered in visible JSX
//                   (child expression or a visible attribute expression).
//   banned_field_label - the SAME typed field published as a label in visible
//                   rendered text ("Confidence score: 82%") instead of as a
//                   property access. Without this the render gate is trivially
//                   bypassed by retyping the machinery as prose, which would
//                   let the frontend publish a calibrated-sounding readout the
//                   backend contract does not produce. Its phrase list is
//                   DERIVED from the vocabulary artifact — a banned_phrases
//                   entry that names a humanized banned_fields entry — never a
//                   hand-kept list, so the two lists cannot drift apart. Only
//                   phrases naming a typed field survive; every other phrase
//                   died with the presentation gates.
//
// The vocabulary artifact banned_vocabulary.json keeps ALL its lists: its
// banned_phrases / banned_standalone_words still bind the BACKEND evidence
// surfaces (app/api/routes/players.py runtime suppression, the Surface-3
// regen validator, counter-argument tests). This scanner now consumes only
// banned_fields. Generated clients (src/lib/) and the vocabulary artifact are
// excluded so backend-shaped field names never false-positive.
//
// Suppression hatch: a finding on line L is suppressed iff line L or L-1 carries
// a `banned-language-ok: <reason>` marker with a non-empty reason (auditable
// escape for an intentionally rendered field). An empty reason never suppresses.
//
// Fail-closed: any finding OR a parse/read error exits non-zero. Output is one
// sorted line per finding so CI results are deterministic.
//
// Usage: node scripts/check-banned-language.mjs [--vocabulary <path>] [--root <path>]
//   --root may be a single file or a directory. Defaults: the committed
//   vocabulary artifact and the authored frontend src/ tree.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { basename, extname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const SCRIPT_DIR = resolve(fileURLToPath(import.meta.url), "..");
const FRONTEND_ROOT = resolve(SCRIPT_DIR, "..");
// CSS was scanned only for presentation language (generated `content:` text);
// with the presentation gates repealed, only TS/TSX can render a typed field.
const SCAN_EXTENSIONS = new Set([".ts", ".tsx"]);
const VISIBLE_ATTRIBUTES = new Set(["aria-label", "title", "alt", "placeholder"]);
const SKIP_DIRS = new Set(["node_modules", "dist", ".git"]);

function parseArgs(argv) {
  const out = { vocabulary: null, root: null };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--vocabulary") out.vocabulary = argv[(i += 1)];
    else if (argv[i] === "--root") out.root = argv[(i += 1)];
  }
  return out;
}

const args = parseArgs(process.argv.slice(2));
const vocabularyPath = args.vocabulary
  ? resolve(args.vocabulary)
  : resolve(FRONTEND_ROOT, "src", "shell", "banned_vocabulary.json");
const rootPath = args.root ? resolve(args.root) : resolve(FRONTEND_ROOT, "src");

let vocabulary;
try {
  vocabulary = JSON.parse(readFileSync(vocabularyPath, "utf8"));
} catch (error) {
  process.stderr.write(`scanner_error vocabulary_unreadable ${vocabularyPath}: ${error.message}\n`);
  process.exit(2);
}

const bannedFields = new Set(vocabulary.banned_fields ?? []);

function escapeRegExp(literal) {
  return literal.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// DERIVED display twins of the banned FIELDS: every banned_phrases entry that
// names a humanized banned_fields entry as a whole word. "confidence" ->
// "confidence score", "dynasty_tier" -> "dynasty tier", "recommended_action" ->
// "recommended action". Phrases naming no typed field ("sell high", "buy low",
// "must start") are presentation language and are NOT collected — they died
// with the phrase gate. Deriving rather than hard-coding means a vocabulary
// change can never leave the render gate and the label gate out of step.
function deriveFieldDisplayTwins(fields, phrases) {
  const humanized = [...fields].map((field) => ({
    field,
    name: field.replace(/_/g, " ").toLowerCase(),
  }));
  const twins = new Map();
  for (const phrase of phrases) {
    const lower = String(phrase).toLowerCase();
    for (const { field, name } of humanized) {
      if (new RegExp(`\\b${escapeRegExp(name)}\\b`).test(lower)) {
        twins.set(lower, field);
        break;
      }
    }
  }
  return twins;
}

const fieldDisplayTwins = deriveFieldDisplayTwins(
  bannedFields,
  vocabulary.banned_phrases ?? [],
);

const findings = [];
const fileTextCache = new Map();

function relPath(file) {
  return relative(process.cwd(), file) || file;
}

function record(file, line, column, gate, detail) {
  findings.push({ file, line, column, gate, detail });
}

function isExcluded(file) {
  const posix = file.split(sep).join("/");
  if (posix.includes("/src/lib/")) return true;
  const base = basename(file);
  if (base === "banned_vocabulary.json") return true;
  if (/\.(test|spec)\.[jt]sx?$/.test(base)) return true;
  return false;
}

// Visible JSX expression gate: a banned terminal property name rendered as a
// field in a visible position.
function scanRenderedExpression(file, sourceFile, expression) {
  const visit = (node) => {
    if (ts.isPropertyAccessExpression(node) && bannedFields.has(node.name.text)) {
      const { line, character } = sourceFile.getLineAndCharacterOfPosition(
        node.getStart(sourceFile),
      );
      record(file, line + 1, character + 1, "banned_field_render", node.name.text);
    }
    ts.forEachChild(node, visit);
  };
  visit(expression);
}

function isJsxChild(node) {
  const parent = node.parent;
  return parent && (ts.isJsxElement(parent) || ts.isJsxFragment(parent));
}

// Visible rendered TEXT gate: the same typed field published as a label.
// `text` must be the verbatim source slice starting at `startPos` so the
// reported line:column lands on the phrase itself.
function scanVisibleText(file, sourceFile, text, startPos) {
  if (fieldDisplayTwins.size === 0) return;
  const lower = text.toLowerCase();
  for (const [twin, field] of fieldDisplayTwins) {
    let index = lower.indexOf(twin);
    while (index !== -1) {
      const { line, character } = sourceFile.getLineAndCharacterOfPosition(
        startPos + index,
      );
      record(file, line + 1, character + 1, "banned_field_label", `${field} as "${twin}"`);
      index = lower.indexOf(twin, index + twin.length);
    }
  }
}

// String-ish literals inside a visible expression are rendered text too:
// {"Confidence score"} / {`Dynasty tier: ${t}`} reach the screen exactly as a
// bare JSX text child does. +1 steps past the opening quote/backtick/`}` so the
// literal's own text aligns with the source offset.
function scanVisibleLiterals(file, sourceFile, expression) {
  const visit = (node) => {
    if (
      ts.isStringLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      ts.isTemplateHead(node) ||
      ts.isTemplateMiddle(node) ||
      ts.isTemplateTail(node)
    ) {
      scanVisibleText(file, sourceFile, node.text, node.getStart(sourceFile) + 1);
    }
    ts.forEachChild(node, visit);
  };
  visit(expression);
}

function scanTypeScript(file, text, scriptKind) {
  const sourceFile = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, scriptKind);
  if (sourceFile.parseDiagnostics && sourceFile.parseDiagnostics.length > 0) {
    record(file, 0, 0, "scanner_error", "parse_error");
    return;
  }

  const walk = (node) => {
    if (ts.isJsxAttribute(node) && node.initializer) {
      const name = node.name.getText(sourceFile);
      if (VISIBLE_ATTRIBUTES.has(name)) {
        const initializer = node.initializer;
        if (ts.isJsxExpression(initializer) && initializer.expression) {
          scanRenderedExpression(file, sourceFile, initializer.expression);
          scanVisibleLiterals(file, sourceFile, initializer.expression);
        } else if (ts.isStringLiteral(initializer)) {
          scanVisibleText(
            file,
            sourceFile,
            initializer.text,
            initializer.getStart(sourceFile) + 1,
          );
        }
      }
    } else if (ts.isJsxExpression(node) && isJsxChild(node) && node.expression) {
      scanRenderedExpression(file, sourceFile, node.expression);
      scanVisibleLiterals(file, sourceFile, node.expression);
    } else if (ts.isJsxText(node)) {
      // Verbatim source slice: JsxText carries its own leading whitespace, so
      // pos..end is exactly what the reader sees.
      scanVisibleText(file, sourceFile, sourceFile.text.slice(node.pos, node.end), node.pos);
    }
    ts.forEachChild(node, walk);
  };
  walk(sourceFile);
}

function scanFile(file) {
  if (isExcluded(file)) return;
  const ext = extname(file);
  if (!SCAN_EXTENSIONS.has(ext)) return;
  let text;
  try {
    text = readFileSync(file, "utf8");
  } catch (error) {
    record(file, 0, 0, "scanner_error", `unreadable: ${error.message}`);
    return;
  }
  fileTextCache.set(file, text);
  scanTypeScript(file, text, ext === ".tsx" ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
}

function walkDirectory(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name)) walkDirectory(join(dir, entry.name));
    } else if (entry.isFile()) {
      scanFile(join(dir, entry.name));
    }
  }
}

try {
  const stats = statSync(rootPath);
  if (stats.isDirectory()) walkDirectory(rootPath);
  else scanFile(rootPath);
} catch (error) {
  process.stderr.write(`scanner_error root_unreadable ${rootPath}: ${error.message}\n`);
  process.exit(2);
}

// Auditable suppression hatch: a finding on line L is suppressed iff line L or
// line L-1 carries a `banned-language-ok: <reason>` marker with a NON-EMPTY
// reason (after stripping trailing comment terminators). An empty reason never
// suppresses. scanner_error findings are never suppressible.
function lineHasReasonedMarker(lineText) {
  if (typeof lineText !== "string") return false;
  const match = lineText.match(/banned-language-ok:(.*)/);
  if (!match) return false;
  const reason = match[1].replace(/[\s*/}]+$/, "").trim();
  return reason.length > 0;
}

function isSuppressed(finding) {
  if (finding.gate === "scanner_error") return false;
  const text = fileTextCache.get(finding.file);
  if (text === undefined) return false;
  const lines = text.split(/\r?\n/);
  const lineNo = finding.line;
  return (
    lineHasReasonedMarker(lines[lineNo - 1]) ||
    (lineNo >= 2 && lineHasReasonedMarker(lines[lineNo - 2]))
  );
}

const reported = findings
  .filter((finding) => !isSuppressed(finding))
  .map((f) => `${relPath(f.file)}:${f.line}:${f.column} ${f.gate} ${f.detail}`);

if (reported.length > 0) {
  reported.sort();
  process.stdout.write(`${reported.join("\n")}\n`);
  process.exit(1);
}
process.exit(0);
