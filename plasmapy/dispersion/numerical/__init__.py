"""
The `~plasmapy.dispersion` subpackage contains functionality associated with
plasma dispersion relations, numerical solvers and analytical solutions.
"""
__all__ = [
    "plasma_dispersion_func",
    "plasma_dispersion_func_deriv",
    "hollweg",
]

from plasmapy.dispersion.dispersionfunction import (
    plasma_dispersion_func,
    plasma_dispersion_func_deriv,
)

from plasmapy.dispersion.numerical.hollweg import hollweg
