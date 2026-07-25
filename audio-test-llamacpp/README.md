# Audio Q&A with llama.cpp

Ask questions about (or transcribe) a local audio file using a local
[llama.cpp](https://github.com/ggerganov/llama.cpp) server with an
audio-capable model (tested with `gemma-4-12b-it`, which handles audio
through the same `--mmproj` projector used for vision).

## Requirements

- Python 3.10+
- A running llama.cpp server on port 8080, started **with a multimodal
  projector** (`--mmproj`) so it can accept audio input.

## Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. Start your llama.cpp server with multimodal support

```bash
./llama-server -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL \
  --mmproj-hf unsloth/gemma-4-12b-it-GGUF \
  --port 8080

# or with local files
./llama-server -m models/gemma-4-12b-it-UD-Q4_K_XL.gguf \
  --mmproj models/mmproj-F16.gguf \
  --port 8080
```

### 2. Ask about an audio file

```bash
python ask_audio.py apps_sample-data_journal1.wav
python ask_audio.py apps_sample-data_journal1.wav "Transcribe this audio word for word."
python ask_audio.py apps_sample-data_journal1.wav --max-tokens 1024 --show-reasoning
```

The script prints the model's answer followed by a timing summary (prefill,
generation, tokens/s) — the same format used in `../image-test-llamacpp`.

---

## Configuration

| Variable / flag | Default | Description |
|---|---|---|
| `LLAMACPP_HOST` (env var) | `localhost` | Host/IP of the llama.cpp server, e.g. `LLAMACPP_HOST=192.168.1.50 python ask_audio.py ...` |
| `--max-tokens` | `2048` | Completion token budget |
| `--show-reasoning` | off | Print the model's `<think>` content, if the server returns any |

---

## How it works

1. **Local audio → base64** — `llama_client.encode_audio()` reads the file and
   base64-encodes its raw bytes; the file extension becomes the `format` field
   (`wav`, `mp3`, ...). Audio never leaves your machine except to your own
   local llama.cpp server.
2. **OpenAI-style audio request** — the audio becomes an
   `{"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"}}`
   content part, alongside a `{"type": "text", ...}` question, in a single
   `/v1/chat/completions` call.
3. **Timing** — llama.cpp returns detailed timings (`prompt_ms`, `predicted_ms`,
   tokens/s) in the response; the script prints these after the answer.
