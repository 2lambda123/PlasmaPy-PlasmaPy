#!/usr/bin/env python
import os
import sys
from itertools import chain
import builtins

from setuptools import setup
from setuptools.config import read_configuration

# Append cwd for pip 19
sys.path.append(os.path.abspath("."))
import ah_bootstrap  # noqa

from astropy_helpers.setup_helpers import register_commands, get_package_info
from astropy_helpers.version_helpers import generate_version_py

# Create a dictionary with setup command overrides. Note that this gets
# information about the package (name and version) from the setup.cfg file.
cmdclass = register_commands()

################################################################################
# Programmatically generate some extras combos.
################################################################################
extras = read_configuration("setup.cfg")['options']['extras_require']

# Dev is everything
extras['dev'] = list(chain(*extras.values()))

# All is everything but tests and docs
exclude_keys = ("tests", "docs", "dev")
ex_extras = dict(filter(lambda i: i[0] not in exclude_keys, extras.items()))
# Concatenate all the values together for 'all'
extras['all'] = list(chain.from_iterable(ex_extras.values()))

# Get configuration information from all of the various subpackages.
# See the docstring for setup_helpers.update_package_files for more
# details.
package_info = get_package_info()
setup(extras_require=extras, use_scm_version=True, cmdclass=cmdclass, **package_info)
