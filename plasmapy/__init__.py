"""
Welcome to the `plasmapy` package, an open source community-developed Python
package for the plasma community.  Documentation is available in the docstrings
and online at https://docs.plasmapy.org (accessible also using the
:func:`~plasmapy.online_help` function).
"""
__all__ = [
    "online_help",
    "diagnostics",
    "formulary",
    "particles",
    "plasma",
    "simulation",
    "utils",
    "__version__",
    "__citation__",
]

import sys
import pkg_resources

from . import (
    diagnostics,
    formulary,
    particles,
    plasma,
    simulation,
    utils,
)

# Enforce Python version check during package import.
# This is the same check as the one at the top of setup.py
if sys.version_info < tuple((int(val) for val in "3.6".split("."))):
    raise Exception("PlasmaPy does not support Python < {}".format(3.6))

# Packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------

# define version
try:
    # this places a runtime dependency on setuptools
    #
    # note: if there's any distribution metadata in your source files, then this
    #       will find a version based on those files.  Keep distribution metadata
    #       out of your repository unless you've intentionally installed the package
    #       as editable (e.g. `pip install -e {plasmapy_directory_root}`),
    #       but then __version__ will not be updated with each commit, it is
    #       frozen to the version at time of install.
    __version__ = pkg_resources.get_distribution("plasmapy").version
except pkg_resources.DistributionNotFound:
    # package is not installed
    fallback_version = "unknown"
    try:
        # code most likely being used from source
        # if setuptools_scm is installed then generate a version
        from setuptools_scm import get_version

        __version__ = get_version(
            root="..", relative_to=__file__, fallback_version=fallback_version
        )
        del get_version
        warn_add = "setuptools_scm failed to detect the version"
    except ModuleNotFoundError:
        # setuptools_scm is not installed
        __version__ = fallback_version
        warn_add = "setuptools_scm is not installed"

    if __version__ == fallback_version:
        from warnings import warn

        warn(
            f"plasmapy.__version__ not generated (set to 'unknown'), PlasmaPy is "
            f"not an installed package and {warn_add}.",
            RuntimeWarning,
        )

        del warn
    del fallback_version, warn_add

# ----------------------------------------------------------------------------


__citation__ = (
    "Instructions on how to cite and acknowledge PlasmaPy are provided in the "
    "online documentation at: http://docs.plasmapy.org/en/latest/about/citation.html"
)


def online_help(query):
    """
    Search the online PlasmaPy documentation for the given query from plasmapy.org
    Opens the results in the default web browser.
    Requires an active Internet connection.
    Redirects to Astropy.units in case of query 'unit' or 'units'

    Parameters
    ----------
    query : str
        The search query.
    """
    from urllib.parse import urlencode
    import webbrowser

    url = (
        "http://docs.plasmapy.org/en/stable/search.html?"
        "{0}&check_keywords=yes&area=default"
    ).format(urlencode({"q": query}))

    if query.lower() in ("unit", "units"):
        url = "http://docs.astropy.org/en/stable/units/"

    webbrowser.open(url)


del pkg_resources, sys
