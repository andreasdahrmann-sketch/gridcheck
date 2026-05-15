#!/usr/bin/env node
/**
 * Guardrail: Node 20 + Next 14 only. Fails on Node 24+ or Next 15+.
 * Run: npm run verify:toolchain (from frontend/)
 */
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(__dirname, "..");
const pkgPath = join(frontendRoot, "package.json");

const errors = [];
const warnings = [];

function parseNodeMajor(version) {
  const m = /^v?(\d+)/.exec(version);
  return m ? Number(m[1]) : NaN;
}

const nodeMajor = parseNodeMajor(process.version);
if (nodeMajor === 24 || nodeMajor >= 25) {
  errors.push(
    `Node ${process.version} is unsupported (Next 14 + Vercel target Node 20 LTS). Use Node 20.x (see frontend/.nvmrc).`,
  );
} else if (nodeMajor !== 20) {
  warnings.push(
    `Node ${process.version} is not the pinned toolchain (expected 20.x). CI/Vercel use Node 20.`,
  );
}

let pkg;
try {
  pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
} catch (e) {
  errors.push(`Cannot read ${pkgPath}: ${e.message}`);
  process.exit(1);
}

function checkDep(name, section = "dependencies") {
  const raw = pkg[section]?.[name];
  if (!raw) {
    errors.push(`Missing ${section}.${name} in package.json`);
    return;
  }
  const major = Number(String(raw).replace(/^[\^~>=<]*/, "").split(".")[0]);
  if (name === "next" && major !== 14) {
    errors.push(
      `next must stay on 14.x (found "${raw}"). Do not bump to Next 15 without explicit migration + Node matrix check.`,
    );
  }
  if (name === "eslint-config-next") {
    const nextRaw = pkg.devDependencies?.["eslint-config-next"] ?? pkg.dependencies?.next;
    const nextVer = pkg.dependencies?.next;
    if (nextVer && raw !== nextVer) {
      warnings.push(
        `eslint-config-next (${raw}) should match next (${nextVer}) exactly.`,
      );
    }
    if (major !== 14) {
      errors.push(`eslint-config-next must match next 14.x (found "${raw}").`);
    }
  }
}

checkDep("next");
checkDep("eslint-config-next", "devDependencies");

const enginesNode = pkg.engines?.node;
if (!enginesNode || !/(^20\.x$|20\.0\.0|<21)/.test(String(enginesNode))) {
  warnings.push(`package.json engines.node should pin Node 20.x (found: ${enginesNode ?? "missing"}).`);
}

if (warnings.length) {
  console.warn("[verify:toolchain] warnings:\n" + warnings.map((w) => `  - ${w}`).join("\n"));
}

if (errors.length) {
  console.error("[verify:toolchain] FAILED:\n" + errors.map((e) => `  - ${e}`).join("\n"));
  process.exit(1);
}

const ls = spawnSync(
  process.platform === "win32" ? "npm.cmd" : "npm",
  ["ls", "next", "react", "react-dom", "--depth=0"],
  { cwd: frontendRoot, encoding: "utf8", shell: process.platform === "win32" },
);

if (ls.status !== 0) {
  warnings.push("npm ls next react react-dom failed (node_modules missing?). Run npm ci.");
  if (ls.stderr) console.warn(ls.stderr.trim());
} else {
  console.log(ls.stdout.trim());
}

console.log(
  "[verify:toolchain] OK ? Node 20.x toolchain, Next 14.x pinned. (Capacitor native:* scripts need Node 22+ via npx @capacitor/cli.)",
);
process.exit(0);
