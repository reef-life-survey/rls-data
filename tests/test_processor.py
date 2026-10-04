import json
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from rls.processor import _create_species_file, _read_survey_data


@pytest.fixture()
def survey_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "species_name": ["Labroides dimidiatus", "Acanthurus nigrofuscus"],
            "data_type_code": [0, 1],
        }
    )


@pytest.fixture()
def species_json_data() -> list[dict[str, Any]]:
    return [
        {
            "scientific_name": "Labroides dimidiatus",
            "slug": "labroides-dimidiatus",
            "main_common_name": "Cleaner wrasse",
            "photos": [
                {
                    "large_url": "https://images.reeflifesurvey.com/cleaner-wrasse.w1000.jpg",
                }
            ],
        },
        {
            "scientific_name": "Acanthurus nigrofuscus",
            "slug": "acanthurus-nigrofuscus",
        },
    ]


def test_create_species_file_with_photos(
    survey_data: pd.DataFrame, species_json_data: list[dict[str, Any]]
) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        dst_dir = Path(tmp_dir)
        _create_species_file(survey_data, species_json_data, dst_dir)
        result = json.loads((dst_dir / "api-species.json").read_text())

    assert set(result.keys()) == {"Labroides dimidiatus", "Acanthurus nigrofuscus"}
    assert result["Labroides dimidiatus"] == [
        "Labroides dimidiatus",
        "Cleaner wrasse",
        "https://reeflifesurvey.com/species/labroides-dimidiatus/",
        0,
        ["https://images.reeflifesurvey.com/cleaner-wrasse.w1000.jpg"],
    ]
    assert result["Acanthurus nigrofuscus"] == [
        "Acanthurus nigrofuscus",
        "",
        "https://reeflifesurvey.com/species/acanthurus-nigrofuscus/",
        1,
        [],
    ]


def test_create_species_file_missing_species(survey_data: pd.DataFrame) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        dst_dir = Path(tmp_dir)
        _create_species_file(survey_data, [], dst_dir)
        result = json.loads((dst_dir / "api-species.json").read_text())

    assert result["Labroides dimidiatus"] == ["Labroides dimidiatus", "", None, 0, []]
    assert result["Acanthurus nigrofuscus"] == [
        "Acanthurus nigrofuscus",
        "",
        None,
        1,
        [],
    ]


def test_read_survey_data_maps_species_and_filters(tmp_path: Path) -> None:
    (tmp_path / "species_list.csv").write_text(
        "species_id,species_name,class,family,superseded_ids\n"
        "10,Labroides dimidiatus,Actinopterygii,Labridae,\n"
        '20,Latropiscis purpurissatus,Actinopterygii,Aulopidae,"183, 184"\n'
    )
    site = "Australia,Cape Howe,Temperate Australasia,Batemans,BMP-S1,Brush Island,RLS"
    (tmp_path / "observations.csv").write_text(
        "species_id,survey_id,country,ecoregion,realm,location,site_code,site_name,"
        "program,method_id,latitude,longitude,total\n"
        f"10,1,{site},1,-35.5,150.4,3\n"
        # supersceded
        f"184,1,{site},2,-35.5,150.4,2\n"
        # missing in species list
        f"999,1,{site},1,-35.5,150.4,5\n"
        # excluded method
        f"10,2,{site},7,-35.5,150.4,4\n"
    )

    survey_data = _read_survey_data(tmp_path)

    assert survey_data[["survey_id", "species_name", "family", "total"]].to_dict(
        "records"
    ) == [
        {
            "survey_id": 1,
            "species_name": "Labroides dimidiatus",
            "family": "Labridae",
            "total": 3,
        },
        {
            "survey_id": 1,
            "species_name": "Latropiscis purpurissatus",
            "family": "Aulopidae",
            "total": 2,
        },
    ]
