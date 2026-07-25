#!/usr/bin/env python3
"""
Ask a question about a local audio file using a local llama.cpp server at
http://localhost:8080/v1/chat/completions.

Usage:
    python ask_audio.py path/to/audio.wav
    python ask_audio.py path/to/audio.wav "Transcribe this audio."
    python ask_audio.py path/to/audio.wav --max-tokens 1024
"""

import argparse
import sys

from llama_client import audio_content, call_model, print_timing_summary


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio_path", help="Path to a local audio file (wav/mp3/...).")
    parser.add_argument(
        "question", nargs="?", default="Transcribe this audio and summarize its content.",
        help="Question to ask about the audio (default: transcribe + summarize).",
    )
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument(
        "--show-reasoning", action="store_true",
        help="Print the model's <think> reasoning content, if any.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": args.question},
                audio_content(args.audio_path),
            ],
        }
    ]

    print(f"Asking about {args.audio_path!r}: {args.question}")
    result = call_model(messages, max_tokens=args.max_tokens)

    if args.show_reasoning and result["reasoning"]:
        print("\n--- Reasoning ---")
        print(result["reasoning"])

    print("\n--- Answer ---")
    print(result["content"] or "(empty response)")

    print_timing_summary(result)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
