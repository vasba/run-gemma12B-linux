#!/usr/bin/env python3
"""
Ask a question about a local image using a local llama.cpp server at
http://localhost:8080/v1/chat/completions.

Usage:
    python ask_image.py path/to/image.jpg
    python ask_image.py path/to/image.jpg "What breed is this dog?"
    python ask_image.py path/to/image.jpg --max-tokens 1024
"""

import argparse
import sys

from llama_client import call_model, image_content, print_timing_summary


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_path", help="Path to a local image file (jpg/png/webp/...).")
    parser.add_argument(
        "question", nargs="?", default="Describe this image in detail.",
        help="Question to ask about the image (default: describe it).",
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
                image_content(args.image_path),
            ],
        }
    ]

    print(f"Asking about {args.image_path!r}: {args.question}")
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
