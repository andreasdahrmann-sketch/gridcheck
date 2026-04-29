// engine/skill-loader.js
// Lädt Skills (MD) und Rules (JSON) aus dem Dateisystem
// v1.0.0

const fs = require('fs');
const path = require('path');

class SkillLoader {
  constructor(baseDir = path.join(__dirname, '..')) {
    this.baseDir = baseDir;
    this.skills = {};
    this.rules = {};
  }

  loadRules(name) {
    const file = path.join(this.baseDir, 'rules', `${name}.rules.json`);
    if (!fs.existsSync(file)) {
      throw new Error(`Rules-Datei nicht gefunden: ${file}`);
    }
    const raw = fs.readFileSync(file, 'utf8');
    const parsed = JSON.parse(raw);
    this.rules[name] = parsed;
    return parsed;
  }

  loadSkill(name) {
    const file = path.join(this.baseDir, 'skills', `${name}.skill.md`);
    if (!fs.existsSync(file)) {
      throw new Error(`Skill-Datei nicht gefunden: ${file}`);
    }
    const content = fs.readFileSync(file, 'utf8');
    this.skills[name] = { name, content, loadedAt: new Date().toISOString() };
    return this.skills[name];
  }

  load(name) {
    const skill = this.loadSkill(name);
    const rules = this.loadRules(name);
    return { skill, rules };
  }
}

module.exports = SkillLoader;
