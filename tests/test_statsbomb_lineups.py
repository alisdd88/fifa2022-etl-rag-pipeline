"""Tests for StatsBomb lineup preprocessing."""

import pandas as pd
import pytest

from src.etl.preprocessing import statsbomb


def write_match_table(processed_dir) -> None:
    """Write the minimum processed match table needed by lineup preprocessing."""
    statsbomb_dir = processed_dir / "statsbomb"
    statsbomb_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "canonical_id": "2022_final_argentina_france",
                "statsbomb_match_id": 3869685,
                "home_team": "Argentina",
                "away_team": "France",
            }
        ]
    ).to_csv(statsbomb_dir / "match.csv", index=False)


def sample_lineups() -> pd.DataFrame:
    """Return lineup rows covering nickname and full-name display behavior."""
    return pd.DataFrame(
        [
            {
                "player_id": 5503,
                "player_name": "Lionel Andrés Messi Cuccittini",
                "player_nickname": "Lionel Messi",
                "jersey_number": 10,
                "country": "Argentina",
                "cards": [],
                "positions": [],
                "match_id": 3869685,
                "team": "Argentina",
            },
            {
                "player_id": 2972,
                "player_name": "Marcus Thuram",
                "player_nickname": None,
                "jersey_number": 26,
                "country": "France",
                "cards": [],
                "positions": [],
                "match_id": 3869685,
                "team": "France",
            },
        ]
    )


def test_transform_lineups_maps_match_and_builds_display_name(
    tmp_path, monkeypatch
) -> None:
    """Lineups retain approved fields and use the full-name fallback."""
    write_match_table(tmp_path)
    monkeypatch.setattr(statsbomb, "PROCESSED_DATA_DIR", tmp_path)

    statsbomb.transform_lineups(sample_lineups())

    result = pd.read_csv(tmp_path / "statsbomb" / "lineups.csv")
    assert list(result.columns) == [
        "canonical_id",
        "statsbomb_match_id",
        "player_id",
        "player_name",
        "player_nickname",
        "player_display_name",
        "jersey_number",
        "country",
        "team",
    ]
    assert result["canonical_id"].eq("2022_final_argentina_france").all()
    assert result["player_display_name"].tolist() == [
        "Lionel Messi",
        "Marcus Thuram",
    ]
    assert pd.isna(result.loc[1, "player_nickname"])


def test_transform_lineups_rejects_team_outside_linked_match(
    tmp_path, monkeypatch
) -> None:
    """A lineup team must be one of the linked match's two teams."""
    write_match_table(tmp_path)
    monkeypatch.setattr(statsbomb, "PROCESSED_DATA_DIR", tmp_path)
    lineups = sample_lineups()
    lineups.loc[0, "team"] = "Croatia"

    with pytest.raises(ValueError, match="team must belong"):
        statsbomb.transform_lineups(lineups)
