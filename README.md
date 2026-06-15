Copied from: https://dev.to/0xkoji/run-gemma-4-12b-on-wsl2-with-llamacpp-1o2m

1. update WSL environment
sudo apt update && sudo apt upgrade -y
2. install dependencies
If you don't use -hf option, you don't need to install libssl-dev in this step.

sudo apt install build-essential cmake git libssl-dev -y
If nvidia-smi shows a GPU/GPUs on your terminal, you will need to install the tooklit. This will take some time.

sudo apt install nvidia-cuda-toolkit -y
3. clone the repo
Build llama-cli and llama-server. This step also will take some time.
If you don't plan to use -hf option, you don't need to use -DLLAMA_OPENSSL=ON.

check the number of cores

nproc --all
16
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DLLAMA_OPENSSL=ON
cmake --build build --config Release -j 16

# no GPU
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build
cmake --build build --config Release -j 16
4. run the model
Run gemma-4-12b-it with cli and server.


unsloth/gemma-4-12b-it-GGUF · Hugging Face
We’re on a journey to advance and democratize artificial intelligence through open source and open science.

huggingface.co
./build/bin/llama-cli -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL
> hello

[Start thinking]
The user said "hello".
The user is initiating a conversation.
Respond politely and offer assistance.

    *   "Hello! How can I help you today?"
    *   "Hi there! What's on your mind?"
    *   "Hello! Is there anything I can assist you with?"
[End thinking]

Hello! How can I help you today?

[ Prompt: 19.5 t/s | Generation: 11.8 t/s ]
or run web-ui

./build/bin/llama-server -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL --port 8080
optional download model from huggingface
mkdir -p models
wget -O models/gemma-4-12b-it-UD-Q4_K_XL.gguf https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/resolve/main/gemma-4-12b-it-UD-Q4_K_XL.gguf

## Image and file requests

Images and other non-text inputs are not sent by adding a plain file path to the prompt. The server has to be started with the matching multimodal projector file, and the request body has to include a multimodal `content` array.

### 1. Let `-hf` download the model and projector when possible

Recent `llama.cpp` builds can discover and download the matching `mmproj` from the same Hugging Face repository when you start a multimodal-capable program such as `llama-server` with `-hf`. This is the simplest option because the model and projector are stored in the normal Hugging Face cache together.

```bash
./build/bin/llama-server \
  -hf unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL \
  -c 8192 \
  --port 8080
```

Watch the startup log. It should mention both the model GGUF and an `mmproj` GGUF. If the server starts in text-only mode, update `llama.cpp` and rebuild it, or use the explicit `--mmproj` fallback below.

If you want to disable projector auto-loading for a text-only run, add `--no-mmproj`.

### 2. Fallback: download and pass the projector explicitly

If automatic `-hf` projector discovery does not work for your build or repository, download the `mmproj` file from the same Hugging Face repository and quantization family as the model weights when possible:

```bash
mkdir -p models
wget -O models/mmproj-gemma-4-12b.gguf \
  https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/resolve/main/mmproj-gemma-4-12b.gguf
```

If that URL changes, open the model repository in a browser and download the file whose name starts with `mmproj`. Image or audio requests will fail if this file is missing or mismatched.

Then start `llama-server` with the local projector path:

```bash
./build/bin/llama-server \
  -m ~/models/gemma-4-12b-it-UD-Q4_K_XL.gguf \
  --mmproj ~/models/mmproj-gemma-4-12b.gguf \
  -c 8192 \
  --port 8080
```

### 3. Send an image request with `curl`

Use an OpenAI-compatible chat completions request. The image can be a public URL or a base64 `data:` URL.

Public image URL example:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-12b-it",
    "messages": [
      {
        "role": "user",
        "content": [
          { "type": "text", "text": "Describe this image in detail." },
          {
            "type": "image_url",
            "image_url": {
              "url": "https://example.com/photo.jpg"
            }
          }
        ]
      }
    ]
  }'
```

Local image file example:

```bash
IMAGE_B64=$(base64 -w 0 ./photo.jpg)

curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"gemma-4-12b-it\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": [
          { \"type\": \"text\", \"text\": \"What is in this image?\" },
          {
            \"type\": \"image_url\",
            \"image_url\": {
              \"url\": \"data:image/jpeg;base64,${IMAGE_B64}\"
            }
          }
        ]
      }
    ]
  }"
```

For a PNG file, change the prefix to `data:image/png;base64,${IMAGE_B64}`.

### 4. Send an image request from Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed",
)

response = client.chat.completions.create(
    model="gemma-4-12b-it",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.com/photo.jpg",
                    },
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)
```

### What about PDFs, text files, and other files?

The OpenAI-style `image_url` content part is for images. For other local files, read the file yourself and put the text into the prompt. For example:

```bash
FILE_TEXT=$(python3 - <<'PY'
from pathlib import Path
print(Path("notes.txt").read_text())
PY
)

curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"gemma-4-12b-it\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"Summarize this file:\\n\\n${FILE_TEXT}\"
      }
    ]
  }"
```

For PDFs, first extract the text with a tool such as `pdftotext`, then include the extracted text in the message. If the PDF page is a scanned image, convert the page to an image and send it as an `image_url` data URL instead.


## Run in codex

## configure codex

Step 1. Install codex
First install codex.

Step 2. Create .codex folder
We need to create config.toml to use local llm with llama.cpp. First we need to run codex

codex
You don't need to set up anything here. You just need to hit ctrl + c.

Step 3. Create config.toml
Once you run Codex, your WSL will have .codex folder.
You can use whatever you like.

vim ~/.codex/config.toml
config.toml

[model_providers.llama]
name = "llama.cpp"
base_url = "http://localhost:8080/v1"
wire_api = "responses"
stream_idle_timeout_ms = 10000000

### download model
as above

### start llama.server
./build/bin/llama-server -m ~/models/gemma-4-12b-it-UD-Q4_K_XL.gguf  -c 100000 --port 8080


### start codex
codex --model ~/models/gemma-4-12b-it-UD-Q4_K_XL.gguf -c model_provider=llama --search --dangerously-bypass-approvals-and-sandbox
