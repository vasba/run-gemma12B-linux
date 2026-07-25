#!/usr/bin/env python3
"""
Compare two local images using a local llama.cpp server at
http://localhost:8080/v1/chat/completions.

Usage:
    python compare_images.py image1.jpg image2.jpg
    python compare_images.py before.png after.png "What changed between these?"
    python compare_images.py a.jpg b.jpg --max-tokens 1024
"""

import argparse
import sys

from llama_client import call_model, image_content, print_timing_summary

DEFAULT_PROMPT = (
    "You are given two images, labeled Image 1 and Image 2. "
    "Compare them and describe: (1) what is similar, (2) what is different, "
    "and (3) any notable differences in quality, composition, or content."
)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image1_path", help="Path to the first local image file.")
    parser.add_argument("image2_path", help="Path to the second local image file.")
    parser.add_argument(
        "prompt", nargs="?", default=DEFAULT_PROMPT,
        help="Comparison question/instruction (default: general similarities/differences).",
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
                {"type": "text", "text": args.prompt},
                {"type": "text", "text": "Image 1:"},
                image_content(args.image1_path),
                {"type": "text", "text": "Image 2:"},
                image_content(args.image2_path),
            ],
        }
    ]

    print(f"Comparing {args.image1_path!r} vs {args.image2_path!r}")
    print(f"Prompt: {args.prompt}")
    result = call_model(messages, max_tokens=args.max_tokens)

    if args.show_reasoning and result["reasoning"]:
        print("\n--- Reasoning ---")
        print(result["reasoning"])

    print("\n--- Comparison ---")
    print(result["content"] or "(empty response)")

    print_timing_summary(result)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
