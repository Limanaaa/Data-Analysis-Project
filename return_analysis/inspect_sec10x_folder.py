import os
import re
import pandas as pd
from config import TARGET_YEAR

def inspect_sec10x_folder(year: int) -> pd.DataFrame:
    folder_path = fr"D:\HEC\Courses\TM3\Data\Project 2\data\data\{year}\QTR4_10-K_files"

    pattern = re.compile(
        r"^(?P<filing_date>\d{8})_"
        r"(?P<form_type>[^_]+)_"
        r"edgar_data_"
        r"(?P<cik>\d+)_"
        r"(?P<accession>[^.]+)\.txt$"
    )

    records = []

    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    for file_name in os.listdir(folder_path):
        if not file_name.endswith(".txt"):
            continue

        match = pattern.match(file_name)
        if match:
            records.append({
                "file_name": file_name,
                "file_path": os.path.join(folder_path, file_name),
                "filing_date": match.group("filing_date"),
                "form_type": match.group("form_type"),
                "cik": match.group("cik"),
                "accession_number": match.group("accession"),
            })
        else:
            records.append({
                "file_name": file_name,
                "file_path": os.path.join(folder_path, file_name),
                "filing_date": None,
                "form_type": None,
                "cik": None,
                "accession_number": None,
            })

    df = pd.DataFrame(records)
    return df


if __name__ == "__main__":
    df = inspect_sec10x_folder(TARGET_YEAR)

    print(f"TARGET_YEAR = {TARGET_YEAR}")
    print(f"Number of files: {len(df)}")
    print("\nSample rows:")
    print(df.head(20))

    print("\nMissing parsing count:")
    print(df[["filing_date", "form_type", "cik", "accession_number"]].isna().sum())

    output_path = f"sec10k_file_index_{TARGET_YEAR}.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")