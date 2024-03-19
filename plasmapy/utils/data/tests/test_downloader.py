import os
import warnings
from pathlib import Path

import numpy as np
import pytest

from plasmapy.utils.data.downloader import Downloader


@pytest.fixture()
def downloader_validated(tmp_path):
    auth_token = os.environ["GITHUB_TOKEN"]
    auth = ("plasmapyapi", auth_token)
    return Downloader(directory=tmp_path, api_auth=auth)


def test_api_token(downloader_validated):
    """
    Test whether the API connection is valid
    """
    limit, used = downloader_validated._api_usage
    assert limit >= 5000


@pytest.fixture()
def downloader_unvalidated(tmp_path):
    return Downloader(directory=tmp_path, validate=False)


test_urls = [
    # Test with a page we know is up if the tests are running
    ("https://github.com/PlasmaPy/PlasmaPy", None),
    # Test with a known 404
    ("https://www.google.com/404", ValueError),
]


@pytest.mark.parametrize(("url", "expected"), test_urls)
def test_http_request(downloader_validated, url, expected):
    """
    Test exceptions from http downloader
    """
    if expected is None:
        downloader_validated._http_request(url)
    else:
        with pytest.raises(expected):
            downloader_validated._http_request(url)


def test_blob_file(downloader_validated):
    """
    Test the read and write blob file routines
    """
    # Add a key to the blob file dict
    test_str = "abc123"
    downloader_validated._blob_dict["test_key"] = test_str
    # Write it to the file
    downloader_validated._write_blobfile()

    # Change the key but don't write to file again
    downloader_validated._blob_dict["test_key"] = "not the same string"

    # Read from file and confirm value was restored
    downloader_validated._read_blobfile()
    assert downloader_validated._blob_dict["test_key"] == test_str


def test_update_blob_entry(downloader_validated):
    """
    Test the logic in the _update_blob_entry function
    """
    dl = downloader_validated

    # Initialize with all None
    dl._update_blob_entry("f1")
    assert "f1" in dl._blob_dict
    assert dl._blob_dict["f1"]["local_sha"] is None
    assert dl._blob_dict["f1"]["repo_sha"] is None
    assert dl._blob_dict["f1"]["download_url"] is None

    dl._update_blob_entry("f1", local_sha="1", repo_sha="2", download_url="3")
    assert "f1" in dl._blob_dict
    assert dl._blob_dict["f1"]["local_sha"] == "1"
    assert dl._blob_dict["f1"]["repo_sha"] == "2"
    assert dl._blob_dict["f1"]["download_url"] == "3"


test_files = [
    # Test downloading a file
    ("NIST_PSTAR_aluminum.txt", None),
    # Test with a different file type
    ("plasmapy_logo.png", None),
    # Test an h5 file
    ("test.h5", None),
    # Test that trying to download a file that doesn't exist raises an
    # exception.
    ("not-a-real-file.txt", ValueError),
]


@pytest.mark.parametrize(
    "downloader", ["downloader_validated", "downloader_unvalidated"]
)
@pytest.mark.parametrize(("filename", "expected"), test_files)
def test_get_file(filename, expected, downloader, request) -> None:
    """Test the get_file function."""

    # Get the downloader fixture based on the string name provided
    dl = request.getfixturevalue(downloader)

    # Scilence warnings from files not found on the repository
    warnings.filterwarnings("ignore", category=UserWarning)

    filepath = dl._filepath(filename)

    if expected is not None:
        with pytest.raises(expected):
            dl.get_file(filename)
    else:
        # Download data (or check that it already exists)
        assert dl.get_file(filename) == filepath

        # Get the file again, already existing so it doesn't download it again
        assert dl.get_file(filename) == filepath


@pytest.mark.parametrize(
    "downloader", ["downloader_validated", "downloader_unvalidated"]
)
def test_get_local_only_fle(tmp_path, downloader, request):
    """
    Test various file retrieval modes
    """

    # Get the downloader fixture based on the string name provided
    dl = request.getfixturevalue(downloader)

    # Silence warnings from files not found on the repository
    warnings.filterwarnings("ignore", category=UserWarning)

    # Retrieve a local file that isn't on the remote
    # First create the file
    filename = "not_on_the_repo.txt"
    filepath = Path(tmp_path, filename)
    with filepath.open("w") as f:
        f.write("Not data")

    # Try getting it now that it exists but isn't in the blob file
    assert dl.get_file(filename) == filepath

    # Add it to the blob file
    dl._update_blob_entry(filename, local_sha="123")
    dl._write_blobfile()

    # Now try retrieving it again
    assert dl.get_file(filename) == filepath

    # Error is raised when a file isn't local or on the remote
    with pytest.raises(ValueError):
        dl.get_file("not_anywhere.txt")


def test_get_file_NIST_PSTAR_datafile(downloader_validated) -> None:
    """Test getting a particular file and checking for known contents"""

    # Silence warnings from files not found on the repository
    warnings.filterwarnings("ignore", category=UserWarning)

    # Download data (or check that it already exists)
    path = downloader_validated.get_file("NIST_PSTAR_aluminum.txt")

    arr = np.loadtxt(path, skiprows=7)
    assert np.allclose(arr[0, :], np.array([1e-3, 1.043e2]))


def test_at_most_one_api_call(downloader_validated) -> None:
    """
    Test that at most one API call is made over multiple queries
    """
    # Silence warnings from files not found on the repository
    warnings.filterwarnings("ignore", category=UserWarning)

    files = ["NIST_PSTAR_aluminum.txt", "plasmapy_logo.png", "test.h5"]

    limit, used0 = downloader_validated._api_usage

    for file in files:
        downloader_validated.get_file(file)

    limit, used1 = downloader_validated._api_usage

    assert used1 <= used0 + 1


def test_creating_another_downloader(downloader_validated):
    """
    Test creating a second downloader in the same directory.
    This will test reading in the existing blob file.
    """

    dl2 = Downloader(directory=downloader_validated._download_directory)

    filename = "NIST_PSTAR_aluminum.txt"
    filepath = dl2._filepath(filename)

    assert dl2.get_file(filename) == filepath


def test_ensure_update_blob_dict_runs(downloader_validated):
    """
    Ensure the _update_blob_dict method gets run if it hasn't already.
    """

    # Only run this test if the downloader fixture hasn't already updated
    # form the repo (so tests remain limited to 1 api call)
    # It seems that sometimes this can happen, in which case this test
    # is necessary to cover that method
    if not downloader_validated._updated_blob_file_from_repo:
        # Reset timer so it doesn't prevent a dict update
        downloader_validated._blob_dict["_timestamp"] = 0

        # Update the dict
        downloader_validated._update_repo_blob_dict()
