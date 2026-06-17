# PDF Financial Data Extractor

Extracts financial data from a PDF report using a local [llama.cpp](https://github.com/ggerganov/llama.cpp) server and outputs structured JSON.

## Requirements

- Python 3.10+
- A running llama.cpp server on port 8080
- A thinking/reasoning-capable model (tested with `gemma-4-12b-it`)

## Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. Start your llama.cpp server

```bash
./llama-server -m your-model.gguf --port 8080 --ctx-size 65536
```

### 2. Run the script

```bash
# default PDF bundled in the repo
python extract_financial.py

# any other PDF
python extract_financial.py path/to/your-report.pdf
```

The extracted data is printed to the terminal and saved to `volvo_trucks_financial_data.json`.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PDF_PATH` | `5349601-...pdf` | Path to the input PDF (overridden by CLI arg) |
| `API_URL` | `http://localhost:8080/v1/chat/completions` | llama.cpp endpoint |
| `MAX_TOKENS` | `16384` | Token budget for JSON output |

### Context window note

The full PDF text is sent in a single request. `MAX_TOKENS=16384` works for PDFs up to ~100 pages.
For larger PDFs you may need to increase it — make sure `--ctx-size` on the server is large enough
to fit both the prompt and the response.

---

## Output

Results are written to `volvo_trucks_financial_data.json` in the working directory. Example structure:

```json
{
  "_timings": { ... },
  "volvo_trucks_group": {
    "net_sales": {
      "q1_2026_sek_m": 75372,
      "q1_2025_sek_m": 82248,
      "change_pct": -8
    },
    "adjusted_operating_margin_pct": {
      "q1_2026": 10.1,
      "q1_2025": 10.3
    },
    "deliveries_trucks": {
      "q1_2026_units": 47504,
      "q1_2025_units": 48833,
      "change_pct": -3
    }
  }
}
```

---

## Timing

The script prints a timing summary at the end of every run:

```text
--- Timing summary ---
  PDF read + parse : 0.1s
  Model prefill    : 28.7s
  Model generation : 99.4s  (27.5 tok/s)
  Total wall clock : 131.6s
  Tokens used      : 42147 prompt + 2736 completion
```

Timing data is also saved in the output JSON under `_timings`:

```json
{
  "_timings": {
    "wall_clock_s": 131.44,
    "prompt_tokens": 42147,
    "completion_tokens": 2736,
    "prefill_s": 28.72,
    "generation_s": 99.42,
    "tokens_per_sec": 27.5,
    "total_wall_clock_s": 131.56
  }
}
```

**What affects speed:**
- `MAX_TOKENS` — higher = more time; reduce if the model finishes before hitting the limit
- Model size / quantization — smaller models generate faster
- `--ctx-size` on the server — does not affect generation speed directly

---

## How it works

1. **PDF → text** — `pymupdf` extracts all text from the PDF pages.
2. **Single request** — the full text is sent to `/v1/chat/completions` in one call.
3. **Prefill trick** — the assistant turn is pre-seeded with `{` so the model starts
   outputting JSON immediately, bypassing the internal `<think>` reasoning phase entirely.
   Without this, Gemma 4 (a thinking model) exhausts the entire token budget on reasoning
   and produces no visible output.
4. **JSON extraction** — a bracket-depth parser finds the largest valid, non-placeholder
   JSON object in the response. If the output is truncated, `_repair_json()` closes
   unclosed braces/brackets before parsing.
