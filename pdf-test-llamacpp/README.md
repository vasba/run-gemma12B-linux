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

### 2. Edit the script to point to your PDF

Open `extract_financial.py` and change the `PDF_PATH` variable at the top:

```python
PDF_PATH = "your-report.pdf"
```

### 3. Run the script

```bash
python extract_financial.py
```

The extracted data is printed to the terminal and saved to `volvo_trucks_financial_data.json`.

---

## Using a different PDF as input

You can pass any PDF directly from the command line without editing the script:

```bash
python extract_financial.py path/to/your-report.pdf
```

To support this, update the `main()` function's first line to read from `sys.argv`:

```python
PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "5349601-volvo-group---report-on-the-first-quarter-2026.pdf"
```

Or just change `PDF_PATH` at the top of the file before running.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PDF_PATH` | `5349601-...pdf` | Path to the input PDF |
| `API_URL` | `http://localhost:8080/v1/chat/completions` | llama.cpp endpoint |
| `MAX_TOKENS` | `16384` | Token budget for the model (reasoning + JSON output) |

### Context window note

The full PDF text is sent in a single request. The default `MAX_TOKENS=16384` works for PDFs up to ~100 pages. For larger PDFs you may need to increase it — make sure your llama.cpp server's `--ctx-size` is large enough to fit both the prompt and the response.

---

## Output

Results are written to `volvo_trucks_financial_data.json` in the working directory. Example structure:

```json
{
  "volvo_trucks_group": {
    "net_sales_msek": {
      "q1_2026": 75372,
      "q1_2025": 82248,
      "change_pct": -8
    },
    "adjusted_operating_margin_pct": {
      "q1_2026": 10.1,
      "q1_2025": 10.3
    },
    "deliveries_units": {
      "q1_2026": 47504,
      "q1_2025": 48833,
      "change_pct": -3
    }
  }
}
```

## Timing

The script prints a timing summary at the end of every run:

```
--- Timing summary ---
  PDF read + parse : 0.1s
  Model prefill    : 0.9s
  Model generation : 340.2s  (27.3 tok/s)
  Total wall clock : 341.2s
  Tokens used      : 929 prompt + 9284 completion
```

Timing data is also stored inside the output JSON under the `_timings` key:

```json
{
  "_timings": {
    "wall_clock_s": 341.1,
    "prompt_tokens": 929,
    "completion_tokens": 9284,
    "prefill_s": 0.9,
    "generation_s": 340.2,
    "tokens_per_sec": 27.3,
    "total_wall_clock_s": 341.2
  },
  ...
}
```

**What affects speed:**
- `MAX_TOKENS` — higher = more time; reduce if the model finishes before hitting the limit
- Model size / quantization — smaller models generate faster
- `--ctx-size` on the server — doesn't affect generation speed directly

## How it works

1. **PDF → text**: `pymupdf` extracts all text from the PDF.
2. **Single request**: the full text is sent to the llama.cpp `/v1/chat/completions` endpoint in one call.
3. **Reasoning model handling**: the model (Gemma 4 thinking) reasons internally before outputting JSON. The script reads from `content` first, then falls back to extracting JSON embedded inside `reasoning_content` if needed.
4. **JSON extraction**: a bracket-depth parser finds the first valid, non-placeholder JSON object in the response.
