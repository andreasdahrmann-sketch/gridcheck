import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import ts from "typescript";

async function loadSafeNextPathModule() {
  const source = await readFile(new URL("./safe-next-path.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2020,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const dataUrl = `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`;
  return import(dataUrl);
}

const { safeNextPath } = await loadSafeNextPathModule();

test("safeNextPath keeps same-origin path targets", () => {
  assert.equal(safeNextPath("/settings?plan=basic#billing", "/projects"), "/settings?plan=basic#billing");
});

test("safeNextPath rejects external and protocol-like targets", () => {
  assert.equal(safeNextPath("//evil.example/phish", "/projects"), "/projects");
  assert.equal(safeNextPath("https://evil.example/phish", "/projects"), "/projects");
  assert.equal(safeNextPath("javascript:alert(1)", "/projects"), "/projects");
  assert.equal(safeNextPath("/\\evil.example", "/projects"), "/projects");
});

test("safeNextPath falls back to a known safe default if fallback is unsafe", () => {
  assert.equal(safeNextPath(null, "https://evil.example"), "/projects");
});
