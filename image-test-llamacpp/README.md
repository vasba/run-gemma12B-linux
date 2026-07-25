# Image Q&A / Comparison with llama.cpp

Ask questions about a local image, or compare two local images, using a local
[llama.cpp](https://github.com/ggerganov/llama.cpp) server with a vision-capable
model (tested with `gemma-4-12b-it`).

## Requirements

- Python 3.10+
- A running llama.cpp server on port 8080, started **with a multimodal projector**
  (`--mmproj`) so it can accept image input.

## Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. Start your llama.cpp server with vision support

Vision requires the `--mmproj` file in addition to the main model — unsloth's
GGUF repos ship one alongside the model (e.g. `mmproj-F16.gguf`).

```bash
./llama-server -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL \
  --mmproj-hf unsloth/gemma-4-12b-it-GGUF \
  --port 8080

# or with local files
./llama-server -m models/gemma-4-12b-it-UD-Q4_K_XL.gguf \
  --mmproj models/mmproj-F16.gguf \
  --port 8080
```

Add `--reasoning off` (or `--chat-template-kwargs '{"enable_thinking":false}'`) if
you want faster, non-thinking responses — see the [repo README](../README.md).

### 2. Ask about one image

```bash
python ask_image.py GoldenGate.png
python ask_image.py GoldenGate.png "What bridge is this and where is it located?"
python ask_image.py GoldenGate.png --max-tokens 1024 --show-reasoning
```

### 3. Compare two images

```bash
python compare_images.py GoldenGate.png red-car.jfif
python compare_images.py GoldenGate.png red-car.jfif "What is the main subject of each image?"
```

Both scripts print the model's answer followed by a timing summary (prefill,
generation, tokens/s), the same format used in `../pdf-test-llamacpp`.

---

## Configuration

| Variable / flag | Default | Description |
|---|---|---|
| `LLAMACPP_HOST` (env var) | `localhost` | Host/IP of the llama.cpp server, e.g. `LLAMACPP_HOST=192.168.1.50 python ask_image.py ...` |
| `--max-tokens` | `2048` | Completion token budget |
| `--show-reasoning` | off | Print the model's `<think>` content, if the server returns any |

---

## How it works

1. **Local image → data URI** — `llama_client.encode_image()` reads the file and
   base64-encodes it into a `data:image/...;base64,...` URI. Images never leave
   your machine except to your own local llama.cpp server.
2. **OpenAI-style vision request** — each image becomes an
   `{"type": "image_url", "image_url": {"url": "data:..."}}` content part,
   alongside `{"type": "text", ...}` parts, in a single `/v1/chat/completions` call.
   `compare_images.py` sends both images labeled "Image 1" / "Image 2" in one message
   so the model can reason about both together.
3. **Timing** — llama.cpp returns detailed timings (`prompt_ms`, `predicted_ms`,
   tokens/s) in the response; both scripts print these after the answer.
