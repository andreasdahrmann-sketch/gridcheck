/**
 * Generates PWA PNG icons from public/icons/icon.svg.
 *
 * Requires Node 20.x (see .nvmrc and package.json engines) and devDependency `sharp`.
 * Run: npm run icons:png
 */
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const iconsDir = join(root, "public", "icons");
const svgPath = join(iconsDir, "icon.svg");

if (!existsSync(svgPath)) {
  console.error(`Missing source SVG: ${svgPath}`);
  process.exit(1);
}

const svg = readFileSync(svgPath);

const sizes = [
  { size: 192, filename: "icon-192x192.png" },
  { size: 512, filename: "icon-512x512.png" },
];

for (const { size, filename } of sizes) {
  const outPath = join(iconsDir, filename);
  await sharp(svg).resize(size, size).png().toFile(outPath);
  console.log(`OK ${filename} (${size}x${size})`);
}
