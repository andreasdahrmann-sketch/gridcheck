// test-validator.js
const SkillLoader = require('../engine/skill-loader');
const InputValidator = require('../engine/validators/input-validation');

const loader = new SkillLoader();
const { skill, rules } = loader.load('input-validation');

console.log(`âœ… Skill geladen: ${skill.name} (${skill.content.length} chars)`);
console.log(`âœ… Rules geladen: v${rules.version}, ${rules.rules.length} Regeln\n`);

const validator = new InputValidator(rules);

// Test 1: GÃ¼ltiger Input
console.log('--- Test 1: GÃ¼ltiger Input ---');
console.log(validator.validate({
  projectName: 'PV Musterhof',
  applicantName: 'Max Muster',
  connectionLevel: 'MV',
  requestedCapacityKw: 500,
  estimatedAvailableCapacityKw: 800,
  loadProfileKnown: true,
  siteSecured: true
}));

// Test 2: Fehlerhafter Input
console.log('\n--- Test 2: Fehlerhafter Input ---');
console.log(validator.validate({
  projectName: '',
  connectionLevel: 'XX',
  requestedCapacityKw: -5
}));
