"""Synthesize Q&A fine-tuning pairs from PDF documents using Claude, and write them
as a fine-tuning-ready JSONL file (one {"messages": [...]} example per line).

Uses the same Claude client/provider configured for the app (app.core.config.settings,
including CLAUDE_PROVIDER=foundry) so this respects whatever Azure AI Foundry / Anthropic
setup is already in .env.

Usage:
    .venv/Scripts/python.exe scripts/generate_finetune_jsonl.py path/to/file.pdf --out train.jsonl
    .venv/Scripts/python.exe scripts/generate_finetune_jsonl.py path/to/pdf_dir/ \
        --out train.jsonl --val-out validation.jsonl --val-split 0.1
"""

import argparse
import json
import random
import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.workflow.claude_client import get_client  # noqa: E402

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer questions accurately and concisely using "
    "only the information available to you."
)

QA_GENERATION_SYSTEM = (
    "You generate high-quality question-and-answer training pairs from a source document "
    "excerpt. Questions must be answerable using only the excerpt. Never invent facts, "
    "numbers, names, or details not present in the text. Vary phrasing, question type "
    "(factual, summary, comparison), and difficulty."
)

QA_SCHEMA = {
    "type": "object",
    "properties": {
        "pairs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["pairs"],
    "additionalProperties": False,
}


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start += chunk_size - overlap
    return chunks


def synthesize_qa_pairs(client, model: str, chunk: str, num_pairs: int) -> list[dict]:
    prompt = (
        f"Generate {num_pairs} diverse question-and-answer pairs from the document "
        "excerpt below, suitable for fine-tuning a model on this domain.\n\n"
        f"---\n{chunk}\n---"
    )
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=QA_GENERATION_SYSTEM,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": QA_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        return []
    text = next((block.text for block in response.content if block.type == "text"), None)
    if not text:
        return []
    return json.loads(text)["pairs"]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="PDF file or directory of PDFs")
    parser.add_argument("--out", default="train.jsonl", help="Output JSONL path (or train split path)")
    parser.add_argument("--val-out", default=None, help="If set, writes a held-out validation JSONL here")
    parser.add_argument("--val-split", type=float, default=0.1, help="Fraction of examples reserved for validation")
    parser.add_argument("--pairs-per-chunk", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=1800, help="Characters per chunk sent to the model")
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT, help="System message baked into each training example")
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    input_path = Path(args.input)
    pdf_paths = sorted(input_path.glob("*.pdf")) if input_path.is_dir() else [input_path]
    if not pdf_paths:
        print(f"No PDFs found at {input_path}", file=sys.stderr)
        sys.exit(1)

    client = get_client()
    model = settings.claude_model

    examples: list[dict] = []
    for pdf_path in pdf_paths:
        print(f"Processing {pdf_path.name}...")
        text = extract_text(pdf_path)
        if not text.strip():
            print("  no extractable text (likely a scanned image PDF) — skipping", file=sys.stderr)
            continue

        chunks = chunk_text(text, args.chunk_size, args.chunk_overlap)
        for i, chunk in enumerate(chunks, start=1):
            pairs = synthesize_qa_pairs(client, model, chunk, args.pairs_per_chunk)
            print(f"  chunk {i}/{len(chunks)}: {len(pairs)} pairs")
            for pair in pairs:
                if not pair.get("question") or not pair.get("answer"):
                    continue
                examples.append(
                    {
                        "messages": [
                            {"role": "system", "content": args.system_prompt},
                            {"role": "user", "content": pair["question"]},
                            {"role": "assistant", "content": pair["answer"]},
                        ]
                    }
                )

    if not examples:
        print("No Q&A pairs were generated.", file=sys.stderr)
        sys.exit(1)

    random.seed(args.seed)
    random.shuffle(examples)

    if args.val_out:
        split_idx = max(1, int(len(examples) * (1 - args.val_split)))
        train_examples, val_examples = examples[:split_idx], examples[split_idx:]
    else:
        train_examples, val_examples = examples, []

    write_jsonl(Path(args.out), train_examples)
    print(f"Wrote {len(train_examples)} examples to {args.out}")

    if args.val_out:
        write_jsonl(Path(args.val_out), val_examples)
        print(f"Wrote {len(val_examples)} examples to {args.val_out}")


if __name__ == "__main__":
    main()
