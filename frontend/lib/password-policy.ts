export type PasswordCheck = { label: string; ok: boolean };

/** Mirrors backend validate_password_strength (auth_service.py). */
export function getPasswordPolicyChecks(password: string): PasswordCheck[] {
  return [
    { label: "Mindestens 12 Zeichen", ok: password.length >= 12 },
    { label: "Grossbuchstabe", ok: /[A-Z]/.test(password) },
    { label: "Kleinbuchstabe", ok: /[a-z]/.test(password) },
    { label: "Zahl", ok: /\d/.test(password) },
    { label: "Sonderzeichen", ok: /[^A-Za-z0-9]/.test(password) },
  ];
}

export function isPasswordPolicySatisfied(password: string): boolean {
  return getPasswordPolicyChecks(password).every((check) => check.ok);
}
