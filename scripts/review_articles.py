"""Interactively review raw Guardian articles for match relevance."""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_DIR, RAW_DATA_DIR

RAW_DIR = RAW_DATA_DIR / "articles"
OUTPUT_FILE = DATA_DIR / "metadata/articles" / "relevant_ids.json"


def get_body_snippet(body_text, char_limit=350):
    if not body_text:
        return "[No Body Text Available]"
    if len(body_text) <= char_limit * 2:
        return body_text

    beginning = body_text[:char_limit].replace("\n", " ")
    ending = body_text[-char_limit:].replace("\n", " ")
    return f"{beginning}\n\n  [... SNIPPET TRUNCATED ...]\n\n  {ending}"


def inspect_articles():
    if not os.path.exists(RAW_DIR):
        print(f"Directory '{RAW_DIR}' not found.")
        return

    articles = []
    for filename in sorted(os.listdir(RAW_DIR)):
        if filename.endswith("_raw_file.json"):
            filepath = os.path.join(RAW_DIR, filename)
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                articles.extend(data.get("articles", []))

    print(f"Loaded {len(articles)} articles for inspection.\n")
    relevant_ids = []

    for idx, item in enumerate(articles, 1):
        fields = item.get("fields", {})
        raw_id = item.get("id")
        title = item.get("webTitle", "No Title")
        byline = fields.get("byline", "N/A")
        pub_date = item.get("webPublicationDate", "N/A")
        url = item.get("webUrl", "N/A")
        body = fields.get("bodyText", "")

        print("=" * 80)
        print(f" ARTICLE [{idx}/{len(articles)}]")
        print("=" * 80)
        print(f" ID        : {raw_id}")
        print(f" Title     : {title}")
        print(f" Author    : {byline}")
        print(f" Date      : {pub_date}")
        print(f" URL       : {url}")
        print("-" * 80)
        print(" TEXT SNIPPET (BEGINNING & END):")
        print(f"\n  {get_body_snippet(body)}\n")
        print("-" * 80)

        while True:
            choice = input("Is this article relevant? [y/n]: ").strip().lower()
            if choice in ["y", "yes"]:
                relevant_ids.append(raw_id)
                print(" -> ACCEPTED")
                break
            elif choice in ["n", "no"]:
                print(" -> REJECTED")
                break
            else:
                print(" Please enter 'y' for yes or 'n' for no.")

    # Save output manifest file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(relevant_ids, f, indent=2)

    print("\n" + "=" * 80)
    print(f"INSPECTION COMPLETE. Total accepted: {len(relevant_ids)}/{len(articles)}")
    print(f"Saved relevant IDs to: {OUTPUT_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    inspect_articles()
