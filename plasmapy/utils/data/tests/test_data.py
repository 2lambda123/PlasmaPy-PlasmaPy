import numpy as np
import os
import pytest

from plasmapy.utils.data import data

test_files = [
    ("NIST_PSTAR_aluminum.txt", None),
    ("missing_an_extension", ValueError),
    ("not-a-real-file.img", OSError),
]


@pytest.mark.parametrize("filename,expected", test_files)
def test_get_file_NIST_data(filename, expected):

    # Delete file if it already exists, so the test always downloads it
    dl_path = os.path.join(data._DOWNLOADS_PATH, filename)
    if os.path.exists(dl_path):
        os.remove(dl_path)

    if expected is not None:
        with pytest.raises(expected):
            path = data.get_file(filename)

    else:
        # Download data (or check that it already exists)
        path = data.get_file(filename)

        # For this one file, check that the contents are right manually
        if filename == "NIST_PSTAR_aluminum.txt":
            arr = np.loadtxt(path, skiprows=7)
            assert np.allclose(arr[0, :], np.array([1e-3, 1.043e2]))

        # Get the file again, already existing so it doesn't download it again
        path = data.get_file(filename)
