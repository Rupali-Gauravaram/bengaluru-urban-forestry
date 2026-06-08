"""
Stage 1 — Tree data extraction from IISc PDFs.

Refactored from `Trees of Bengaluru-IISC table extraction.ipynb`. Parses three
source PDFs into structured CSVs:

  * annexure5.pdf                 -> Bengaluru_Tree_Palette.csv   (grid table)
  * CES_TVR_ETR75... (pp.33-38)   -> Ward_wise_tree_details.csv   (grid table)
  * CES_TVR_ETR75 Extract[38-48]  -> Annexure3_Prominent_Trees.csv (free text)

Each step is guarded so a missing PDF skips that step with a warning rather than
crashing the whole pipeline (the PDFs are large and may not always be present).
"""
import re

import pandas as pd
import pdfplumber

from . import config


def extract_tree_palette() -> None:
    """annexure5.pdf -> Bengaluru_Tree_Palette.csv (auto grid detection)."""
    if not config.PDF_ANNEXURE5.exists():
        print(f"[extract_trees] SKIP palette: {config.PDF_ANNEXURE5.name} not found.")
        return

    all_data = []
    with pdfplumber.open(config.PDF_ANNEXURE5) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                all_data.extend(table)

    df = pd.DataFrame(all_data[1:], columns=all_data[0]).replace("\n", " ", regex=True)
    df.to_csv(config.OUT_TREE_PALETTE, index=False)
    print(f"[extract_trees] Tree palette -> {config.OUT_TREE_PALETTE.name}")


def extract_ward_tree_details() -> None:
    """CES_TVR PDF pages 33-38 -> Ward_wise_tree_details.csv."""
    if not config.PDF_CES_FULL.exists():
        print(f"[extract_trees] SKIP ward trees: {config.PDF_CES_FULL.name} not found.")
        return

    all_data = []
    with pdfplumber.open(config.PDF_CES_FULL) as pdf:
        for i, page in enumerate(pdf.pages[32:38]):
            table = page.extract_table()
            if table:
                all_data.extend(table if i == 0 else table[1:])

    df = (
        pd.DataFrame(all_data[1:], columns=all_data[0])
        .replace(r"\n", " ", regex=True)
        .replace(r"\s+", " ", regex=True)
        .dropna(how="all")
    )
    df.to_csv(config.OUT_WARD_TREES, index=False)
    print(f"[extract_trees] Ward tree details ({len(df)} rows) -> {config.OUT_WARD_TREES.name}")


def extract_prominent_trees() -> None:
    """CES_TVR Extract[38-48] free-text -> Annexure3_Prominent_Trees.csv."""
    if not config.PDF_CES_EXTRACT.exists():
        print(f"[extract_trees] SKIP prominent trees: {config.PDF_CES_EXTRACT.name} not found.")
        return

    fields = {
        "Common_Name": r"Common name:\s*(.*)",
        "Family": r"Family:\s*(.*)",
        "Description": r"Description:\s*([\s\S]*?)(?=Flowering:|$)",
        "Flowering": r"Flowering:\s*(.*)",
        "Native": r"Native:\s*(.*)",
        "Location": r"Location:\s*(.*)",
    }

    records = []
    with pdfplumber.open(config.PDF_CES_EXTRACT) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for block in re.split(r"(?=Common name:)", text):
                if "Common name:" not in block:
                    continue
                record = {}
                for col, pattern in fields.items():
                    match = re.search(pattern, block)
                    record[col] = match.group(1).replace("\n", " ").strip() if match else "N/A"
                records.append(record)

    df = pd.DataFrame(records).drop_duplicates(subset=["Common_Name"])
    df.to_csv(config.OUT_PROMINENT_TREES, index=False)
    print(f"[extract_trees] Prominent trees ({len(df)} rows) -> {config.OUT_PROMINENT_TREES.name}")


def run() -> None:
    """Execute all Stage 1 extraction steps."""
    config.ensure_output_dir()
    extract_tree_palette()
    extract_ward_tree_details()
    extract_prominent_trees()


if __name__ == "__main__":
    run()
