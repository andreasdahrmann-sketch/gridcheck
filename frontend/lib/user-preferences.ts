export type HomeModulePreference = "check" | "dashboard";

export type DefaultCustomerTypePreference =
  | ""
  | "projektierer"
  | "speicherbetreiber"
  | "netzbetreiber";

export type UserPreferences = {
  defaultLandingTab: HomeModulePreference;
  defaultCustomerType: DefaultCustomerTypePreference;
  persistCheckDraft: boolean;
  compactProjectCards: boolean;
};

const STORAGE_KEY = "gridcheck_user_preferences";

export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  defaultLandingTab: "check",
  defaultCustomerType: "",
  persistCheckDraft: true,
  compactProjectCards: false,
};

function sanitizePreferences(raw: unknown): UserPreferences {
  if (!raw || typeof raw !== "object") {
    return { ...DEFAULT_USER_PREFERENCES };
  }

  const candidate = raw as Partial<UserPreferences>;

  return {
    defaultLandingTab:
      candidate.defaultLandingTab === "dashboard" ? "dashboard" : DEFAULT_USER_PREFERENCES.defaultLandingTab,
    defaultCustomerType:
      candidate.defaultCustomerType === "projektierer" ||
      candidate.defaultCustomerType === "speicherbetreiber" ||
      candidate.defaultCustomerType === "netzbetreiber"
        ? candidate.defaultCustomerType
        : DEFAULT_USER_PREFERENCES.defaultCustomerType,
    persistCheckDraft:
      typeof candidate.persistCheckDraft === "boolean"
        ? candidate.persistCheckDraft
        : DEFAULT_USER_PREFERENCES.persistCheckDraft,
    compactProjectCards:
      typeof candidate.compactProjectCards === "boolean"
        ? candidate.compactProjectCards
        : DEFAULT_USER_PREFERENCES.compactProjectCards,
  };
}

export function readUserPreferences(): UserPreferences {
  if (typeof window === "undefined") {
    return { ...DEFAULT_USER_PREFERENCES };
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? sanitizePreferences(JSON.parse(raw)) : { ...DEFAULT_USER_PREFERENCES };
  } catch {
    return { ...DEFAULT_USER_PREFERENCES };
  }
}

export function saveUserPreferences(next: UserPreferences): UserPreferences {
  const sanitized = sanitizePreferences(next);

  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized));
  }

  return sanitized;
}

export function resetUserPreferences(): UserPreferences {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
  }

  return { ...DEFAULT_USER_PREFERENCES };
}
