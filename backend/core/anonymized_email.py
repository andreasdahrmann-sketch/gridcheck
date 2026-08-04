"""Reserved DSGVO anonymization email helpers.

Soft-deleted accounts replace the cleartext email with an address under
``@anonymized.local``. That namespace must not be publicly registerable:
a deterministic ``deleted_user_{id}@anonymized.local`` can be pre-reserved
via normal registration and then collide with the unique ``users.email``
constraint when the victim tries Art. 17 deletion.
"""

from __future__ import annotations

import re
import secrets

ANONYMIZED_EMAIL_DOMAIN = "anonymized.local"
_ANONYMIZED_EMAIL_RE = re.compile(
    rf"^deleted_user_\d+(?:_[0-9a-f]+)?@{re.escape(ANONYMIZED_EMAIL_DOMAIN)}$"
)


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_reserved_anonymized_email(email: str) -> bool:
    """True for any address under the internal anonymization domain."""
    normalized = normalize_email(email)
    return normalized.endswith(f"@{ANONYMIZED_EMAIL_DOMAIN}")


def build_anonymized_email(user_id: int) -> str:
    """Collision-resistant replacement email for a soft-deleted account."""
    return f"deleted_user_{int(user_id)}_{secrets.token_hex(8)}@{ANONYMIZED_EMAIL_DOMAIN}"


def looks_like_anonymized_account_email(email: str) -> bool:
    """Stricter pattern match used by tests / diagnostics."""
    return bool(_ANONYMIZED_EMAIL_RE.match(normalize_email(email)))
