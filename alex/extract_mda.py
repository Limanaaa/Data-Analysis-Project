#%%

"""
extract_mda.py
==============
Extracts the "Management's Discussion and Analysis of Financial Condition
and Results of Operations" (MD&A) section from SEC EDGAR full-submission
10-K TXT files (the kind downloaded from:
  https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=...&type=10-K

Usage
-----
    python extract_mda.py <path_to_10k.txt>           # single file
    python extract_mda.py <directory_of_txts/>         # batch mode

Output is saved as  <original_stem>_mda.txt  next to each source file.
A JSON summary (mda_batch_summary.json) is written when running in batch
mode.

How it works
------------
SEC 10-K filings contain embedded HTML or plain-text documents wrapped in
SGML <DOCUMENT> tags.  The script:
  1. Finds the main 10-K document inside the submission.
  2. Strips HTML tags so only readable text remains.
  3. Locates the MD&A start boundary with a ranked list of regex patterns
     (from most-specific to most-permissive).
  4. Locates the end boundary by finding the *next* major Item heading that
     follows MD&A (Item 3, 7A, or 8 depending on what's present).
  5. Writes the extracted text to a file and prints a short summary.
"""

import re
import sys
import json
import logging
from html.parser import HTMLParser
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------
class _TextExtractor(HTMLParser):
    """Minimal HTML → plain-text converter."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_tags = {"script", "style", "head"}
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True
        # Block-level tags → newline
        if tag in {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5"}:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse runs of blank lines to at most two
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def strip_html(text: str) -> str:
    """Return plain text from an HTML string (or pass through plain text)."""
    if not re.search(r"<[a-zA-Z]", text):
        return text  # already plain text
    p = _TextExtractor()
    p.feed(text)
    return p.get_text()


# ---------------------------------------------------------------------------
# EDGAR helpers
# ---------------------------------------------------------------------------
# Patterns that mark the BEGINNING of the MD&A section.
# Ordered most-specific → most-permissive; first match wins.
_MDA_START_PATTERNS: list[re.Pattern] = [
    # "ITEM 7." or "ITEM 7 " followed by MD&A wording (full)
    re.compile(
        r"(?:ITEM\s*7[\.\s]*)"
        r"(?:MANAGEMENT[\u2019']?S\s+DISCUSSION\s+AND\s+ANALYSIS"
        r"\s+OF\s+FINANCIAL\s+CONDITION\s+AND\s+RESULTS\s+OF\s+OPERATIONS)",
        re.IGNORECASE,
    ),
    # Slightly relaxed — tolerates missing "OF FINANCIAL CONDITION…"
    re.compile(
        r"(?:ITEM\s*7[\.\s]*)"
        r"(?:MANAGEMENT[\u2019']?S\s+DISCUSSION\s+AND\s+ANALYSIS)",
        re.IGNORECASE,
    ),
    # No "ITEM 7" prefix, but the full title is present
    re.compile(
        r"MANAGEMENT[\u2019']?S\s+DISCUSSION\s+AND\s+ANALYSIS"
        r"\s+OF\s+FINANCIAL\s+CONDITION\s+AND\s+RESULTS\s+OF\s+OPERATIONS",
        re.IGNORECASE,
    ),
]

# Patterns that mark the END of the MD&A section (the next Item heading).
_MDA_END_PATTERNS: list[re.Pattern] = [
    re.compile(r"ITEM\s*7A[\.\s]+QUANTITATIVE", re.IGNORECASE),
    re.compile(r"ITEM\s*8[\.\s]+FINANCIAL\s+STATEMENTS", re.IGNORECASE),
    re.compile(r"ITEM\s*3[\.\s]+LEGAL\s+PROCEEDINGS", re.IGNORECASE),
    # Generic fallback: any "ITEM N" heading two or more lines after start
    re.compile(r"^\s*ITEM\s+\d+[A-Z]?[\.\s]", re.IGNORECASE | re.MULTILINE),
]


def _find_main_document(raw: str) -> str:
    """
    Extract the text of the primary 10-K document from an EDGAR full-submission
    file.  Falls back to the entire file if no <DOCUMENT> blocks are found.
    """
    # EDGAR wraps each embedded file in <DOCUMENT>...</DOCUMENT>
    doc_blocks = re.findall(
        r"<DOCUMENT>(.*?)</DOCUMENT>", raw, flags=re.DOTALL | re.IGNORECASE
    )
    if not doc_blocks:
        log.warning("No <DOCUMENT> blocks found — treating whole file as document.")
        return raw

    # Try to find the block whose <TYPE> is 10-K (not EX-* or GRAPHIC)
    for block in doc_blocks:
        type_match = re.search(r"<TYPE>\s*10-K", block, re.IGNORECASE)
        if type_match:
            log.debug("Found 10-K <TYPE> block.")
            return block

    # Fall back to the first (usually largest) block
    log.warning("No explicit 10-K TYPE block found; using first <DOCUMENT>.")
    return max(doc_blocks, key=len)


def _extract_text_from_document(doc_text: str) -> str:
    """Strip the EDGAR SGML header lines and convert HTML to plain text."""
    # Remove everything up to the first <HTML> tag (or <TEXT> tag for plain-text docs)
    html_start = re.search(r"<HTML>|<TEXT>", doc_text, re.IGNORECASE)
    if html_start:
        doc_text = doc_text[html_start.start():]

    return strip_html(doc_text)


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------
def extract_mda(filepath: str | Path) -> dict:
    """
    Extract the MD&A section from a single EDGAR 10-K TXT file.

    Returns a dict with keys:
        source      – str  path of the input file
        found       – bool whether the section was found
        start_pos   – int  character index in plain text where MD&A begins
        end_pos     – int  character index where MD&A ends (-1 = end of doc)
        text        – str  the extracted section (empty if not found)
        warnings    – list of warning strings
    """
    filepath = Path(filepath)
    result = {
        "source": str(filepath),
        "found": False,
        "start_pos": -1,
        "end_pos": -1,
        "text": "",
        "warnings": [],
    }

    if not filepath.exists():
        result["warnings"].append(f"File not found: {filepath}")
        return result

    # --- Read file -----------------------------------------------------------
    raw = filepath.read_text(encoding="utf-8", errors="replace")

    # --- Isolate the 10-K document body -------------------------------------
    doc_block = _find_main_document(raw)
    plain = _extract_text_from_document(doc_block)

    # --- Find MD&A start -----------------------------------------------------
    start_match = None
    for pat in _MDA_START_PATTERNS:
        start_match = pat.search(plain)
        if start_match:
            log.debug("MD&A start matched by pattern: %s", pat.pattern[:60])
            break

    if not start_match:
        result["warnings"].append("Could not locate MD&A start heading.")
        return result

    start_pos = start_match.start()
    result["start_pos"] = start_pos

    # --- Find MD&A end -------------------------------------------------------
    # Search only *after* the start heading (skip a few chars to avoid
    # re-matching the same line)
    search_from = start_pos + len(start_match.group())
    end_pos = -1

    for pat in _MDA_END_PATTERNS:
        end_match = pat.search(plain, search_from)
        if end_match:
            # Make sure we're not matching the same heading again
            if end_match.start() > search_from + 100:
                end_pos = end_match.start()
                log.debug("MD&A end matched by pattern: %s", pat.pattern[:60])
                break

    result["end_pos"] = end_pos
    section_text = plain[start_pos:end_pos] if end_pos != -1 else plain[start_pos:]

    # Quick sanity check: section should have some substance
    if len(section_text.strip()) < 200:
        result["warnings"].append(
            f"Extracted section is suspiciously short ({len(section_text)} chars)."
        )

    result["found"] = True
    result["text"] = section_text.strip()
    return result


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def process_file(filepath: str | Path) -> dict:
    """Extract MD&A and write output file.  Returns the result dict."""
    filepath = Path(filepath)
    log.info("Processing: %s", filepath.name)

    result = extract_mda(filepath)

    if result["warnings"]:
        for w in result["warnings"]:
            log.warning("  ⚠  %s", w)

    if result["found"]:
        out_path = filepath.parent / (filepath.stem + "_mda.txt")
        out_path.write_text(result["text"], encoding="utf-8")
        char_count = len(result["text"])
        log.info(
            "  ✓  Saved %s  (%d chars, ~%d words)",
            out_path.name,
            char_count,
            len(result["text"].split()),
        )
        result["output_file"] = str(out_path)
    else:
        log.warning("  ✗  MD&A section not found in %s", filepath.name)
        result["output_file"] = None

    return result


def process_directory(dirpath: str | Path) -> list[dict]:
    """Process all *.txt files in a directory and write a JSON summary."""
    dirpath = Path(dirpath)
    txt_files = sorted(dirpath.glob("*.txt"))
    if not txt_files:
        log.error("No .txt files found in %s", dirpath)
        return []

    results = [process_file(f) for f in txt_files]

    summary_path = dirpath / "mda_batch_summary.json"
    summary_path.write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )
    log.info("Batch summary written to %s", summary_path)

    found = sum(1 for r in results if r["found"])
    log.info("Done: %d / %d files had an MD&A section extracted.", found, len(results))
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    target = Path(sys.argv[1])

    if target.is_dir():
        process_directory(target)
    elif target.is_file():
        process_file(target)
    else:
        log.error("Path does not exist: %s", target)
        sys.exit(1)

def main_analyzer(filepath):
    return extract_mda(filepath)

def save_to_txt(text: str, filepath: str = "output.txt") -> None:
    """
        Save a string to a .txt file
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved to {filepath}")

if __name__ == "__main__":
    file = "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/alex/sec-edgar-filings/0000320193/10-K/0000320193-22-000108/full-submission.txt"
    section = main_analyzer(filepath = file)
    save_to_txt(section["text"], "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/alex/sec-edgar-filings/0000320193/10-K/0000320193-22-000108/output.txt")

# %%
