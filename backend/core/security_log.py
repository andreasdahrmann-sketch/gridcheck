from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("gridcheck.security")


def log_security_event(event: str, **fields: Any) -> None:
    safe_fields = {k: v for k, v in fields.items() if v is not None}
    logger.info("security_event=%s fields=%s", event, safe_fields)
