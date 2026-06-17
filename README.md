Source: https://dev.to/0xkoji/run-gemma-4-12b-on-wsl2-with-llamacpp-1o2m

# Run Gemma 4 12B with llama.cpp

## 1. Update WSL environment

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. Install dependencies

If you don't use the `-hf` option, you don't need `libssl-dev`.

```bash
sudo apt install build-essential cmake git libssl-dev -y
```

If `nvidia-smi` shows a GPU, also install the CUDA toolkit (takes a while):

```bash
sudo apt install nvidia-cuda-toolkit -y
```

## 3. Clone and build llama.cpp

Check the number of cores first:

```bash
nproc --all
```

**With GPU (CUDA):**

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DLLAMA_OPENSSL=ON
cmake --build build --config Release -j 16
```

**Without GPU:**

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build
cmake --build build --config Release -j 16
```

## 4. Run the model

Model: [unsloth/gemma-4-12b-it-GGUF](https://huggingface.co/unsloth/gemma-4-12b-it-GGUF)

**CLI:**

```bash
./build/bin/llama-cli -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL
```

Example interaction:

```text
> hello

[Start thinking]
The user said "hello". Respond politely and offer assistance.
[End thinking]

Hello! How can I help you today?

[ Prompt: 19.5 t/s | Generation: 11.8 t/s ]
```

**Server (web UI + API on port 8080):**

```bash
./build/bin/llama-server -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL --port 8080
```

Or use the Q4_0 variant — standard 4-bit quantization, no unquantization overhead, loads faster:

```bash
./build/bin/Release/llama-server -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_0 -c 100000 --port 8080
```

**Optional — download model manually:**

```bash
mkdir -p models
wget -O models/gemma-4-12b-it-UD-Q4_K_XL.gguf \
  https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/resolve/main/gemma-4-12b-it-UD-Q4_K_XL.gguf
```

---

## Run with Codex

### Step 1 — Install Codex

Install the Codex CLI.

### Step 2 — Create the `.codex` folder

Run `codex` once (then `Ctrl+C`) so it creates `~/.codex/`:

```bash
codex
```

### Step 3 — Create `config.toml`

```bash
vim ~/.codex/config.toml
```

```toml
[model_providers.llama]
name = "llama.cpp"
base_url = "http://localhost:8080/v1"
wire_api = "responses"
stream_idle_timeout_ms = 10000000
```

### Start the server

```bash
./build/bin/llama-server -m ~/models/gemma-4-12b-it-UD-Q4_K_XL.gguf -c 100000 --port 8080
```

### Start Codex

```bash
codex --model ~/models/gemma-4-12b-it-UD-Q4_K_XL.gguf -c model_provider=llama --search --dangerously-bypass-approvals-and-sandbox
```
