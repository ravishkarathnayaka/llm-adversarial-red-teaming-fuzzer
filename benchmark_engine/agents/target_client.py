"""Target Client: Unified wrapper for System Under Test (SUT) supporting Ollama, HTTP API, and Mock LLM."""

import time
from typing import Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from benchmark_engine.mock.mock_llm_server import MockLLMEngine


class TargetResponse(BaseModel):
    text: str
    status_code: int = 200
    latency_ms: float = 0.0
    model: str = "mock-llm"
    error: Optional[str] = None
    raw_payload: Dict = Field(default_factory=dict)


class TargetClient:
    """Client for dispatching evaluation prompts to the target system."""

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        model_name: str = "mock-llm",
        timeout_seconds: float = 30.0,
        api_key: Optional[str] = None,
        use_mock: bool = False,
        mock_mode: str = "hardened",
    ):
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout = timeout_seconds
        self.api_key = api_key
        self.use_mock = use_mock or (endpoint_url is None) or ("mock" in (endpoint_url or "").lower())
        self.mock_engine = MockLLMEngine(mode=mock_mode)

    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        canary_token: Optional[str] = None,
        turn_number: int = 1,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> TargetResponse:
        """Send prompt to target system (Mock engine or real HTTP endpoint)."""
        start_time = time.perf_counter()

        if self.use_mock:
            # Deterministic in-process mock execution (Zero external network dependencies)
            mock_res = self.mock_engine.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                canary_token=canary_token,
                turn_number=turn_number,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TargetResponse(
                text=mock_res.response_text,
                status_code=200,
                latency_ms=elapsed_ms,
                model=f"mock-{self.mock_engine.mode}",
                raw_payload={"mock_type": mock_res.model_type, "refusal": mock_res.is_refusal},
            )

        # Real HTTP / Ollama / OpenAI execution
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = self.endpoint_url or "http://localhost:11434"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # Check endpoint style
                if "/v1/chat/completions" in url:
                    # OpenAI-compatible
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    if chat_history:
                        messages.extend(chat_history)
                    messages.append({"role": "user", "content": prompt})

                    payload = {
                        "model": self.model_name,
                        "messages": messages,
                        "temperature": 0.0,
                    }
                    resp = client.post(url, json=payload, headers=headers)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return TargetResponse(
                            text=content,
                            status_code=resp.status_code,
                            latency_ms=elapsed_ms,
                            model=self.model_name,
                            raw_payload=data,
                        )
                    else:
                        return TargetResponse(
                            text="",
                            status_code=resp.status_code,
                            latency_ms=elapsed_ms,
                            model=self.model_name,
                            error=f"HTTP {resp.status_code}: {resp.text}",
                        )
                else:
                    # Ollama endpoint (/api/generate or base url)
                    gen_url = f"{url.rstrip('/')}/api/generate"
                    payload = {
                        "model": self.model_name,
                        "prompt": prompt,
                        "system": system_prompt or "",
                        "stream": False,
                    }
                    resp = client.post(gen_url, json=payload, headers=headers)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    if resp.status_code == 200:
                        data = resp.json()
                        return TargetResponse(
                            text=data.get("response", ""),
                            status_code=resp.status_code,
                            latency_ms=elapsed_ms,
                            model=self.model_name,
                            raw_payload=data,
                        )
                    else:
                        return TargetResponse(
                            text="",
                            status_code=resp.status_code,
                            latency_ms=elapsed_ms,
                            model=self.model_name,
                            error=f"HTTP {resp.status_code}: {resp.text}",
                        )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return TargetResponse(
                text="",
                status_code=500,
                latency_ms=elapsed_ms,
                model=self.model_name,
                error=str(e),
            )
