#%%

import ollama
import json
import sys
import re
import time
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

MODEL = "llama3.2"
CHUNK_SIZE = 1_000  # words per chunk

# ── Indicators & Prompts ──────────────────────────────────────────────────────

INDICATORS = [
    {
        "id": "financial_stability",
        "name": "Liquidity & Financial Stability",
        "prompt": (
            "Based on this 10-K excerpt, score the company's overall financial stability "
            "and liquidity from -10 (distressed) to +10 (extremely healthy). "
            'Reply with ONLY a JSON object, no explanation outside it: {"score": <integer>, "reason": "<one sentence>"}'
        ),
        "components": ["financial_stability"],
    },
    {
        "id": "business_moat",
        "name": "Business Moat",
        "prompt": (
            "Based on this 10-K excerpt, score the company's overall business moat "
            "by considering three dimensions together: "
            "(1) revenue growth outlook (-10 = severe decline, +10 = strong growth), "
            "(2) competitive strength (-10 = highly vulnerable, +10 = dominant position), "
            "(3) innovation capacity (-10 = stagnating, +10 = highly innovative). "
            "Return a single blended score from -10 to +10 reflecting all three. "
            'Reply with ONLY a JSON object, no explanation outside it: {"score": <integer>, "reason": "<one sentence>"}'
        ),
        "components": ["revenue_growth", "competitive_position", "innovation_rd"],
    },
    {
        "id": "risk_exposure",
        "name": "External Risk Exposure",
        "prompt": (
            "Based on this 10-K excerpt, score the company's overall exposure to external risks "
            "by considering four dimensions together: "
            "(1) regulatory and legal risk (-10 = severe exposure, +10 = well protected), "
            "(2) supply chain resilience (-10 = extremely fragile, +10 = very robust), "
            "(3) geographic and foreign exchange risk (-10 = very high exposure, +10 = well hedged), "
            "(4) macroeconomic sensitivity (-10 = extremely sensitive, +10 = very resilient). "
            "Return a single blended score from -10 to +10 reflecting all four. "
            'Reply with ONLY a JSON object, no explanation outside it: {"score": <integer>, "reason": "<one sentence>"}'
        ),
        "components": ["regulatory_legal", "supply_chain_risk", "geo_currency", "macro_sensitivity"],
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_text(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)
    return path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list:
    words = text.split()
    return [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]


def parse_json_response(raw: str) -> dict:
    """Robustly extract JSON from model output."""
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[^{}]*"score"\s*:\s*-?\d+[^{}]*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"score": 0, "reason": "Could not parse model response."}


def score_indicator_on_chunk(chunk: str, indicator: dict) -> dict:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": f"{indicator['prompt']}\n\nText:\n{chunk}",
            }
        ],
    )
    raw = response["message"]["content"]
    return parse_json_response(raw)


def average_scores(results: list) -> dict:
    scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    reason = results[-1].get("reason", "") if results else ""
    return {"score": avg, "reason": reason}


def score_indicator(text: str, indicator: dict, chunk_size: int = CHUNK_SIZE) -> dict:
    chunks = chunk_text(text, chunk_size=chunk_size)
    if len(chunks) == 1:
        return score_indicator_on_chunk(chunks[0], indicator)
    chunk_results = []
    for i, chunk in enumerate(chunks):
        print(f"      chunk {i+1}/{len(chunks)}...", end=" ", flush=True)
        result = score_indicator_on_chunk(chunk, indicator)
        chunk_results.append(result)
        print(f"score={result.get('score', '?')}")
    return average_scores(chunk_results)


def render_bar(score: float, width: int = 30) -> str:
    half = width // 2
    filled = int(abs(score) / 10 * half)
    if score >= 0:
        bar = " " * half + "█" * filled + " " * (half - filled)
    else:
        bar = " " * (half - filled) + "█" * filled + " " * half
    return f"[{bar}]"


def print_dashboard(results: list) -> None:
    print("\n" + "═" * 72)
    print("  10-K SCORING DASHBOARD")
    print("═" * 72)
    print(f"  {'Indicator':<30} {'Score':>6}  {'Bar':^32}")
    print("─" * 72)
    total = 0
    for r in results:
        score = r["score"]
        total += score
        bar = render_bar(score)
        print(f"  {r['name']:<30} {score:>+6.1f}  {bar}")
        print(f"  {'':30}   ↳ {r['reason']}")
        print()
    avg = total / len(results)
    print("─" * 72)
    print(f"  {'OVERALL SCORE':<30} {avg:>+6.1f}  {render_bar(avg)}")
    print("═" * 72)


def save_json(results: list, filepath: str = "scores.json") -> None:
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Scores saved to {filepath}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(filepath=None, chunk_size=CHUNK_SIZE, path_save_json=None):
    # If no filepath passed programmatically, fall back to CLI
    if filepath is None:
        if len(sys.argv) < 2:
            raise ValueError("Provide a filepath or pass one to main(filepath)")
        filepath = sys.argv[1]

    print(f"\n[→] Loading file: {filepath}")
    text = load_text(filepath)

    word_count = len(text.split())
    print(f"[→] {word_count:,} words loaded ({len(chunk_text(text))} chunk(s))")
    print(f"[→] Running {len(INDICATORS)} indicators on {MODEL}...\n")

    all_results = []

    for i, indicator in enumerate(INDICATORS, 1):
        print(f"  [{i:02d}/{len(INDICATORS)}] {indicator['name']}...")
        start = time.time()

        result = score_indicator(text, indicator, chunk_size=chunk_size)

        elapsed = time.time() - start
        all_results.append({
            "id": indicator["id"],
            "name": indicator["name"],
            "score": result["score"],
            "reason": result["reason"],
            "elapsed_s": round(elapsed, 1),
        })

        print(f"      → score: {result['score']:+} | {result['reason']} ({elapsed:.1f}s)")

    print_dashboard(all_results)

    if path_save_json is not None:
        save_json(all_results, filepath=path_save_json)
    else :
        save_json(all_results)

    return all_results

if __name__ == "__main__":
    file = "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/alex/sec-edgar-filings/0000320193/10-K/0000320193-22-000108/output.txt"
    main(filepath=file, chunk_size=CHUNK_SIZE, path_save_json=None)
# %%
