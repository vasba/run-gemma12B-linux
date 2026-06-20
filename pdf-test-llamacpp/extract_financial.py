#!/usr/bin/env python3
"""
Extract financial data for Volvo Trucks Group from a PDF report
using a local llama.cpp server at http://localhost:8080/v1/chat/completions.

Usage:
    python extract_financial.py [path/to/report.pdf]

Key findings from development
------------------------------
1. Send the full PDF in one request.
   The PDF is ~26k tokens; the model context is 256k. Chunking wastes time and
   produces fragmented results. One request = one coherent extraction.

2. The model (Gemma 4 12B thinking / unsloth GGUF) is a reasoning model.
   By default it spends its entire token budget on internal chain-of-thought
   (reasoning_content) before emitting any visible content. With MAX_TOKENS=16384
   it exhausted the budget thinking and produced zero output.

3. Fix: prefill the assistant turn with '{'.
   Adding {"role": "assistant", "content": "{"} to the messages list tells
   llama.cpp to treat '{' as the start of the assistant reply. The model
   continues from there and outputs JSON directly, bypassing the <think> phase
   entirely. Result: reasoning_len=0, finish_reason=stop, ~130 s total.

4. JSON repair for edge cases.
   If the model still hits the token limit mid-JSON (e.g. with a larger PDF),
   _repair_json() closes unclosed strings/arrays/objects so partial output is
   not silently discarded. extract_json_from_text() also searches both content
   and reasoning_content, skipping template placeholders ("...").

5. Timing.
   llama.cpp returns detailed timings in the response (prompt_ms, predicted_ms,
   tokens/s). These are printed per-run and stored in the _timings key of the
   output JSON for benchmarking across different models or PDFs.
"""

import json
import re
import sys
import time
import requests
import pymupdf  # PyMuPDF


PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "5349601-volvo-group---report-on-the-first-quarter-2026.pdf"
API_URL  = "http://192.168.68.53:8080/v1/chat/completions"
MODEL    = "local-model"   # llama.cpp ignores the model name
MAX_TOKENS = 256000         # large budget so reasoning + JSON both fit


def extract_text_from_pdf(path: str) -> str:
    doc = pymupdf.open(path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def _post(payload: dict, timeout: int) -> dict:
    resp = requests.post(API_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _balanced_json(text: str, start: int) -> str:
    """Extract the balanced JSON object starting at text[start] (must be '{')."""
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    # Truncated — return what we have so caller can decide
    return text[start:]


def extract_json_from_text(text: str) -> str:
    """
    Find the best (largest, non-placeholder) JSON object in arbitrary text.
    Checks markdown ```json blocks first, then bare objects.
    Skips objects containing '...' placeholders (from system-prompt examples).
    """
    candidates = []

    # 1. Collect all ```json ... ``` fenced blocks
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL):
        candidates.append(m.group(1))

    # 2. Collect all top-level balanced { } objects
    pos = 0
    while True:
        start = text.find("{", pos)
        if start == -1:
            break
        obj = _balanced_json(text, start)
        candidates.append(obj)
        pos = start + 1

    # 3. Pick the largest candidate that parses as valid JSON and has no placeholders
    best = ""
    for c in candidates:
        if "..." in c:          # skip template/placeholder objects
            continue
        try:
            json.loads(c)       # must be valid JSON
            if len(c) > len(best):
                best = c
        except json.JSONDecodeError:
            pass

    if best:
        return best

    # 4. No complete valid JSON found — try to repair the largest truncated candidate
    for c in sorted(candidates, key=len, reverse=True):
        if "..." in c or not c.startswith("{"):
            continue
        repaired = _repair_json(c)
        if repaired:
            return repaired

    return ""


def _repair_json(text: str) -> str:
    """
    Attempt to fix a truncated JSON object by closing unclosed strings,
    arrays, and objects. Returns the repaired string if it parses, else "".
    """
    # Remove trailing partial key or comma
    text = re.sub(r',\s*$', '', text.rstrip())
    text = re.sub(r':\s*$', '', text.rstrip())
    # Close any unclosed string
    in_string = False
    escape = False
    stack = []
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            stack.append('}' if ch == '{' else ']')
        elif ch in ('}', ']') and stack:
            stack.pop()

    if in_string:
        text += '"'
    # Close open containers in reverse order
    text += ''.join(reversed(stack))

    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        return ""


def call_model(messages: list[dict]) -> dict:
    """Return {'content': ..., 'reasoning': ..., timings: ...} from the model."""
    t0 = time.perf_counter()
    data = _post({
        "model": MODEL,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.1,
    }, timeout=900)
    elapsed = time.perf_counter() - t0

    choice = data["choices"][0]
    finish_reason = choice.get("finish_reason", "")
    content   = choice["message"].get("content", "") or ""
    reasoning = choice["message"].get("reasoning_content", "") or ""

    # llama.cpp returns detailed timings in the response
    srv_timings = data.get("timings", {})
    prompt_tokens    = data.get("usage", {}).get("prompt_tokens", 0)
    completion_tokens = data.get("usage", {}).get("completion_tokens", 0)
    prompt_ms   = srv_timings.get("prompt_ms", 0)
    predicted_ms = srv_timings.get("predicted_ms", elapsed * 1000)
    tok_per_sec = srv_timings.get("predicted_per_second", 0)

    print(f"  finish_reason={finish_reason}")
    print(f"  tokens        : {prompt_tokens} prompt + {completion_tokens} completion"
          f" = {prompt_tokens + completion_tokens} total")
    print(f"  prefill       : {prompt_ms/1000:.1f}s  ({srv_timings.get('prompt_per_second', 0):.0f} tok/s)")
    print(f"  generation    : {predicted_ms/1000:.1f}s  ({tok_per_sec:.1f} tok/s)")
    print(f"  wall clock    : {elapsed:.1f}s")
    print(f"  content_len={len(content)}, reasoning_len={len(reasoning)}")

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


def main():
    t_start = time.perf_counter()

    print(f"Reading PDF: {PDF_PATH}")
    text = extract_text_from_pdf(PDF_PATH)
    print(f"Extracted {len(text):,} characters (~{len(text)//4:,} tokens) from PDF")

    system_prompt = (
        "You are a financial data extraction assistant. "
        "Extract ALL financial figures, KPIs, and metrics for Volvo Trucks Group from the report. "
        "Use descriptive snake_case keys. Include the unit in the key name where applicable "
        "(e.g. 'net_revenue_msek', 'operating_margin_pct', 'truck_deliveries_units'). "
        "Where a metric has comparison periods (e.g. Q1 2026 vs Q1 2025), represent it as an "
        "object with period keys like {\"q1_2026\": <value>, \"q1_2025\": <value>}. "
        "Extract as many distinct fields as possible. "
        "Return ONLY a valid JSON object — no markdown, no explanation."
    )

    user_prompt = (
        f"Here is the full text of the report:\n\n{text}\n\n"
        "Extract every financial figure, KPI, and metric for Volvo Trucks Group and return a JSON object."
    )

    # Prefill the assistant turn with '{' so the model is forced to emit JSON
    # immediately rather than spending all tokens on internal reasoning first.
    messages = [
        {"role": "system",    "content": system_prompt},
        {"role": "user",      "content": user_prompt},
        {"role": "assistant", "content": "{"},
    ]

    print(f"Sending full document to model (max_tokens={MAX_TOKENS}) …")
    result = call_model(messages)

    content   = result["content"]
    reasoning = result["reasoning"]
    timings   = result["timings"]

    # The assistant turn was prefilled with '{', so prepend it to the content
    # (llama.cpp returns only the *continuation*, not the prefill itself).
    content_full = "{" + content if content and not content.lstrip().startswith("{") else content

    # Try to extract JSON from content first, then from reasoning_content
    raw_json = extract_json_from_text(content_full)
    source = "content"
    if not raw_json and reasoning:
        print("  content empty/no JSON — trying reasoning_content …")
        raw_json = extract_json_from_text(reasoning)
        source = "reasoning_content"

    if not raw_json:
        print("No JSON found in either content or reasoning_content.", file=sys.stderr)
        print("--- content ---", file=sys.stderr)
        print(content[:500] or "(empty)", file=sys.stderr)
        print("--- reasoning_content (first 500 chars) ---", file=sys.stderr)
        print(reasoning[:500] or "(empty)", file=sys.stderr)
        sys.exit(1)

    print(f"  JSON extracted from: {source}")

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        print(raw_json[:300], file=sys.stderr)
        sys.exit(1)

    total_s = time.perf_counter() - t_start
    timings["total_wall_clock_s"] = round(total_s, 2)

    output = {"_timings": timings, **data}

    output_path = "volvo_trucks_financial_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n--- Timing summary ---")
    print(f"  PDF read + parse : {total_s - timings['wall_clock_s']:.1f}s")
    print(f"  Model prefill    : {timings['prefill_s']:.1f}s")
    print(f"  Model generation : {timings['generation_s']:.1f}s  ({timings['tokens_per_sec']} tok/s)")
    print(f"  Total wall clock : {total_s:.1f}s")
    print(f"  Tokens used      : {timings['prompt_tokens']} prompt + {timings['completion_tokens']} completion")
    print(f"\nDone. {len(data)} top-level fields written to {output_path}")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
