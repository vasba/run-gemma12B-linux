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


