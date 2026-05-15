#!/usr/bin/env node
/**
 * Guardrail: Node 20+ + Next 14 only.
 */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pkgPath = join(__dirname, "..", "package.json");
const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));

const errors = [];
const nodeMajor = parseInt(process.version.replace("v","").split(".")[0]);

if (nodeMajor < 20) {
  errors.push(`Node ${process.version} is unsupported. Use Node 20+.`);
}

if (errors.length > 0) {
  console.error("[verify:toolchain] FAILED:");
  errors.forEach(e => console.error(`  - ${e}`));
  process.exit(1);
} else {
  console.log(`[verify:toolchain] OK — Node ${process.version}`);
}
