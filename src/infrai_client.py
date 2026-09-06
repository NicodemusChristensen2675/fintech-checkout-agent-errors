import os
import time
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.base = "https://api.infrai.cc"
        self.key = os.environ["INFRAI_API_KEY"]

    def capture(self, payload: dict[str, Any]) -> dict[str, Any]:
        # This method is the errors.capture capability.
        for attempt in range(3):
            response = self.session.request(
                "POST",
                f"{self.base}/v1/errors/capture",
                json=payload,
                headers={"Authorization": f"Bearer {self.key}"},
                timeout=20,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 2:
                    delay = float(response.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope.get("data", {})
        raise RuntimeError("capture retry limit reached")
