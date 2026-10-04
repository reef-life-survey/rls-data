"""Survey data downloader."""
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import requests

from .util import verify_empty_dir

_logger = logging.getLogger("rls.processor")

# public AODN/NRMN endpoints
S3_ENDPOINTS_URL = (
    "https://nrmn-prod-shared.s3.ap-southeast-2.amazonaws.com/"
    "endpoints/ncbQK0mp5Td7RgpmOGZI"
)

# local file name: s3 source filename
SURVEY_DATA_FILES = {
    "species_list.csv": "ep_species_list.csv",
    "observations.csv": "ep_species_survey_observation.csv",
}


def download_survey_data(survey_data_dir: Path) -> None:
    """Download RLS CSV data files to the given directory, creating it if needed."""
    verify_empty_dir(survey_data_dir)
    results = ThreadPoolExecutor(max_workers=len(SURVEY_DATA_FILES)).map(
        _download_survey_data_file,
        [
            (f"{S3_ENDPOINTS_URL}/{endpoint_name}", survey_data_dir / file_name)
            for file_name, endpoint_name in SURVEY_DATA_FILES.items()
        ],
        # obs are in one file now instead of per-method from geoserver, so allowing more time for this to complete
        timeout=timedelta(minutes=15).total_seconds(),
    )
    for _ in results:
        pass


def _download_survey_data_file(url_and_out_path: tuple[str, Path]) -> None:
    """Download a single survey data file, streaming it to disk."""
    url, out_path = url_and_out_path
    _logger.info("Downloading %s to %s", url, out_path)
    with requests.get(
        url, stream=True, timeout=timedelta(minutes=10).total_seconds()
    ) as response:
        response.raise_for_status()
        with out_path.open("wb") as fp:
            for chunk in response.iter_content(chunk_size=1 << 20):
                fp.write(chunk)
    _logger.info("Saved %s", out_path)
