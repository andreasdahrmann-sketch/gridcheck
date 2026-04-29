// engine/validators/input-validation.js
// Führt Input-Validierung basierend auf rules/input-validation.rules.json aus
// v1.0.0

class InputValidator {
  constructor(rules) {
    if (!rules) throw new Error('InputValidator: rules fehlen');
    this.rules = rules;
    this.version = rules.version;
  }

  validate(input) {
    const errors = [];
    const warnings = [];

    if (!input || typeof input !== 'object') {
      return {
        valid: false,
        errors: [{ id: 'FATAL', message: 'Input ist kein Objekt' }],
        warnings: [],
        rulesVersion: this.version
      };
    }

    for (const rule of this.rules.rules) {
      const val = input[rule.field];

      switch (rule.type) {
        case 'required':
          if (val === undefined || val === null || val === '') {
            errors.push({ id: rule.id, field: rule.field, message: rule.message });
          }
          break;

        case 'enum':
          if (val !== undefined && val !== null && !rule.allowed.includes(val)) {
            errors.push({ id: rule.id, field: rule.field, message: rule.message });
          }
          break;

        case 'number_min':
          if (val !== undefined && val !== null) {
            if (typeof val !== 'number' || isNaN(val) || val < rule.min) {
              errors.push({ id: rule.id, field: rule.field, message: rule.message });
            }
          }
          break;

        case 'warning_if_false':
          if (val === false || val === undefined || val === null) {
            warnings.push({ id: rule.id, field: rule.field, message: rule.message });
          }
          break;

        default:
          warnings.push({
            id: 'UNKNOWN_RULE',
            message: `Unbekannter Rule-Typ: ${rule.type} (${rule.id})`
          });
      }
    }

    // Zusätzlich: Typ-Check
    for (const [field, expectedType] of Object.entries(this.rules.fieldTypes || {})) {
      if (input[field] !== undefined && input[field] !== null) {
        const actualType = typeof input[field];
        if (actualType !== expectedType) {
          errors.push({
            id: 'TYPE_MISMATCH',
            field,
            message: `${field} muss ${expectedType} sein, ist aber ${actualType}`
          });
        }
      }
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
      rulesVersion: this.version
    };
  }
}

module.exports = InputValidator;
