"""
Shared helpers for talking to a local llama.cpp server with audio input,
used by ask_audio.py.
"""

import base64
import os
import time

import requests

API_URL = "http://localhost:8080/v1/chat/completions"
MODEL = "local-model"  # llama.cpp ignores the model name


def encode_audio(path: str) -> tuple[str, str]:
    """Return (base64_data, format) for the audio file at `path`."""
    fmt = os.path.splitext(path)[1].lstrip(".").lower() or "wav"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return b64, fmt


def audio_content(path: str) -> dict:
    data, fmt = encode_audio(path)
    return {"type": "input_audio", "input_audio": {"data": data, "format": fmt}}


def call_model(messages: list[dict], max_tokens: int, timeout: int = 300) -> dict:
    """POST to the chat completions endpoint and return content + timing info."""
    t0 = time.perf_counter()
    resp = requests.post(
        API_URL,
        json={
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    elapsed = time.perf_counter() - t0

    choice = data["choices"][0]
    content = choice["message"].get("content", "") or ""
    reasoning = choice["message"].get("reasoning_content", "") or ""
    finish_reason = choice.get("finish_reason", "")

    srv_timings = data.get("timings", {})
    prompt_tokens = data.get("usage", {}).get("prompt_tokens", 0)
    completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
    prompt_ms = srv_timings.get("prompt_ms", 0)
    predicted_ms = srv_timings.get("predicted_ms", elapsed * 1000)
    tok_per_sec = srv_timings.get("predicted_per_second", 0)

    return {
        "content": content,
        "reasoning": reasoning,
        "finish_reason": finish_reason,
        "timings": {
            "wall_clock_s": round(elapsed, 2),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "prefill_s": round(prompt_ms / 1000, 2),
            "generation_s": round(predicted_ms / 1000, 2),
            "tokens_per_sec": round(tok_per_sec, 1),
        },
    }


def print_timing_summary(result: dict) -> None:
    t = result["timings"]
    print("\n--- Timing summary ---")
    print(f"  finish_reason  : {result['finish_reason']}")
    print(f"  Model prefill  : {t['prefill_s']:.1f}s")
    print(f"  Model generation: {t['generation_s']:.1f}s  ({t['tokens_per_sec']} tok/s)")
    print(f"  Wall clock     : {t['wall_clock_s']:.1f}s")
    print(f"  Tokens used    : {t['prompt_tokens']} prompt + {t['completion_tokens']} completion")
    if result["reasoning"]:
        print(f"  Reasoning chars: {len(result['reasoning'])} (use --show-reasoning to print)")
