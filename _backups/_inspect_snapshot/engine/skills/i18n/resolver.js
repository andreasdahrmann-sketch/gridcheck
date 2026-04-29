const fs = require("fs");
const path = require("path");

const cache = {};

function loadLocale(skill, lang) {
  const key = `${skill}.${lang}`;
  if (cache[key]) return cache[key];

  const file = path.join(__dirname, `${skill}.${lang}.json`);
  if (!fs.existsSync(file)) {
    throw new Error(`i18n-Datei nicht gefunden: ${file}`);
  }
  let raw = fs.readFileSync(file, "utf8");
  // BOM entfernen, falls vorhanden
  if (raw.charCodeAt(0) === 0xFEFF) raw = raw.slice(1);
  try {
    const data = JSON.parse(raw);
    cache[key] = data;
    return data;
  } catch (e) {
    throw new Error(`JSON-Parse-Fehler in ${file}: ${e.message}`);
  }
}

function t(skill, lang, key) {
  const supported = ["de", "en"];
  const useLang = supported.includes(lang) ? lang : "de";
  const data = loadLocale(skill, useLang);
  if (data[key] !== undefined) return data[key];

  // Fallback auf DE
  if (useLang !== "de") {
    const deData = loadLocale(skill, "de");
    if (deData[key] !== undefined) return deData[key];
  }
  return `[missing:${key}]`;
}

module.exports = { t };