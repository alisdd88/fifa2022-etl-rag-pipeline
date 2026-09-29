"""Shared helpers for preprocessing StatsBomb records."""

import json

import pandas as pd


def process_events(events: pd.DataFrame) -> pd.DataFrame:
    """Convert selected StatsBomb events into normalized key-event rows."""

    def get_card(row: pd.Series) -> object:
        """Return the populated card value from a foul or bad-behaviour row."""
        for column in ("foul_committed_card", "bad_behaviour_card"):
            value = row[column]
            if pd.notna(value) and str(value).strip():
                return value
        return None

    # Step 1: Build card rows from fouls and bad-behaviour events with cards.
    non_substitutions = events[events["type"] != "Substitution"].copy()
    non_substitutions["card_value"] = non_substitutions.apply(get_card, axis=1)

    cards = non_substitutions[non_substitutions["card_value"].notna()].copy()
    cards["event_type"] = "card"
    cards["metadata"] = cards.apply(
        lambda row: {
            "card_reason": (
                "foul" if row["type"] == "Foul Committed" else "bad_behaviour"
            ),
            "card_type": row["card_value"],
        },
        axis=1,
    )

    # Step 2: Build match-goal rows and exclude period-5 shootout conversions.
    goals = non_substitutions[
        (non_substitutions["type"] == "Shot")
        & (non_substitutions["shot_outcome"] == "Goal")
        & (non_substitutions["period"].between(1, 4))
    ].copy()
    goals["event_type"] = "goal"
    goals["metadata"] = goals.apply(
        lambda row: {"shot_type": row["shot_type"]},
        axis=1,
    )

    # Step 3: Represent every substitution as paired OUT and IN player actions.
    substitution_rows = []
    substitutions = events[events["type"] == "Substitution"].copy()

    for _, row in substitutions.iterrows():
        substitution_ref_id = str(row["event_id"])

        outgoing = row.copy()
        outgoing["event_id"] = f"{substitution_ref_id}_OUT"
        outgoing["event_type"] = "substitution"
        outgoing["metadata"] = {
            "substitution_type": "OUT",
            "substitution_ref_id": substitution_ref_id,
        }
        substitution_rows.append(outgoing)

        incoming = row.copy()
        incoming["event_id"] = f"{substitution_ref_id}_IN"
        incoming["event_type"] = "substitution"
        incoming["player_id"] = row["substitution_replacement_id"]
        incoming["player"] = row["substitution_replacement"]
        incoming["metadata"] = {
            "substitution_type": "IN",
            "substitution_ref_id": substitution_ref_id,
        }
        substitution_rows.append(incoming)

    processed_substitutions = pd.DataFrame(substitution_rows)
    final_events = pd.concat(
        [cards, goals, processed_substitutions],
        ignore_index=True,
    )

    # Step 4: Store event-specific fields as valid JSON metadata.
    final_events["metadata"] = final_events["metadata"].apply(
        lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True)
    )
    detail_columns = [
        "card_value",
        "foul_committed_penalty",
        "foul_committed_offensive",
        "foul_committed_type",
        "foul_committed_advantage",
        "bad_behaviour_card",
        "foul_committed_card",
        "shot_outcome",
        "shot_saved_to_post",
        "shot_type",
        "substitution_replacement",
        "substitution_replacement_id",
        "substitution_outcome",
        "substitution_outcome_id",
    ]
    final_events = final_events.drop(columns=detail_columns, errors="ignore")

    # Step 5: Keep each match's events in chronological source order.
    return final_events.sort_values(
        by=["match_id", "statsbomb_event_index", "event_id"]
    ).reset_index(drop=True)
