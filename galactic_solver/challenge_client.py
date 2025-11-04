from __future__ import annotations
import os
from typing import Any, Dict, Optional
import httpx

DEFAULT_BASE_URL = os.getenv("CHALLENGE_BASE_URL", "https://recruiting.adere.so").rstrip("/")
HTTP_TIMEOUT = 10.0

class ChallengeClient:
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        # Prefer generic env var
        env_token = os.getenv("CHALLENGE_TOKEN")
        token = token or env_token
        if not token:
            raise RuntimeError("CHALLENGE_TOKEN is not set. Use a .env file or environment variable.")
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._client = httpx.Client(timeout=HTTP_TIMEOUT, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _get(self, path: str) -> Dict[str, Any]:
        resp = self._client.get(f"{self.base_url}{path}")
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._client.post(f"{self.base_url}{path}", json=json)
        resp.raise_for_status()
        return resp.json()

    # Practice endpoint
    def get_test(self) -> Dict[str, Any]:
        return self._get("/challenge/test")

    # Official start
    def start(self) -> Dict[str, Any]:
        return self._get("/challenge/start")

    # Submit solution
    def submit_solution(self, problem_id: str, answer: Any) -> Dict[str, Any]:
        payload = {"problem_id": problem_id, "answer": answer}
        return self._post("/challenge/solution", payload)

    # Chat completion proxy to GPT-4o-mini
    def chat_completion(self, messages: list[dict], model: str = "gpt-4o-mini") -> Dict[str, Any]:
        payload = {"model": model, "messages": messages}
        return self._post("/chat_completion", payload)
