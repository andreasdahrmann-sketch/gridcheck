// src/lib/units.ts
// Zentrales Einheiten- und Konvertierungsmodul (IEC-konform)
// Intern: W, var, VA, V, A, Ohm, m

// === Konverter ===
export const kW_to_W = (kw: number): number => kw * 1000;
export const MW_to_W = (mw: number): number => mw * 1_000_000;
export const W_to_kW = (w: number): number => w / 1000;
export const W_to_MW = (w: number): number => w / 1_000_000;
export const kV_to_V = (kv: number): number => kv * 1000;
export const V_to_kV = (v: number): number => v / 1000;
export const MVA_to_VA = (mva: number): number => mva * 1_000_000;
export const VA_to_MVA = (va: number): number => va / 1_000_000;
export const kVA_to_VA = (kva: number): number => kva * 1000;
export const VA_to_kVA = (va: number): number => va / 1000;
export const km_to_m = (km: number): number => km * 1000;
export const m_to_km = (m: number): number => m / 1000;
export const kA_to_A = (ka: number): number => ka * 1000;
export const A_to_kA = (a: number): number => a / 1000;

// === Elektrische Grundgroessen ===
export function calcS_from_P_cosPhi(p_W: number, cosPhi: number): number {
  return p_W / Math.max(cosPhi, 0.01);
}

export function calcQ_from_P_cosPhi(p_W: number, cosPhi: number): number {
  const phi = Math.acos(Math.min(Math.max(cosPhi, 0.01), 1.0));
  return p_W * Math.tan(phi);
}

export function calcS_from_PQ(p_W: number, q_var: number): number {
  return Math.sqrt(p_W * p_W + q_var * q_var);
}

export function calcI_from_S(s_VA: number, u_V: number): number {
  return s_VA / (Math.sqrt(3) * Math.max(u_V, 1));
}

// === Impedanz ===
export function calcZq(u_V: number, sk_VA: number): number {
  return (u_V * u_V) / Math.max(sk_VA, 1);
}

export function calcZtrafo(uk_pct: number, sr_VA: number, u_V: number): number {
  return (uk_pct / 100) * (u_V * u_V) / Math.max(sr_VA, 1);
}

export function calcRX_from_Z(z_ohm: number, rx_ratio: number): { r: number; x: number } {
  const phi = Math.atan(1 / Math.max(rx_ratio, 0.01));
  const x = z_ohm * Math.sin(phi);
  const r = z_ohm * Math.cos(phi);
  return { r, x };
}

// === Spannungsaenderung (signiert, positiv = Anhebung) ===
export function calcDeltaU_pct(
  p_W: number, q_var: number, r_ohm: number, x_ohm: number, u_V: number, isEinspeisung: boolean
): { delta_u_pct: number; isRise: boolean } {
  const sign = isEinspeisung ? 1 : -1;
  const du = sign * (p_W * r_ohm + q_var * x_ohm) / (u_V * u_V) * 100;
  return { delta_u_pct: Math.round(du * 100) / 100, isRise: du > 0 };
}

// === Kurzschlussstrom ===
export function calcIk(u_V: number, z_ohm: number): number {
  return u_V / (Math.sqrt(3) * Math.max(z_ohm, 0.0001));
}
