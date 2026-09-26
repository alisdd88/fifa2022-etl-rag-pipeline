"""Input and output helpers for pipeline data."""

from pathlib import Path

import pandas as pd


def load_raw_data(path: str | Path) -> pd.DataFrame:
    """Load a record-oriented raw JSON file into a DataFrame."""
    return pd.read_json(Path(path), orient="records")


def save_raw_dataframe(df: pd.DataFrame, path: str | Path) -> None:
    """Save a DataFrame as record-oriented JSON without overwriting raw data."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        raise FileExistsError(f"Raw data file already exists: {output_path}")

    df.to_json(
        output_path,
        orient="records",
        indent=2,
        date_format="iso",
        force_ascii=False,
    )
