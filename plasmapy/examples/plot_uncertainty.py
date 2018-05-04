# coding: utf-8
"""
Uncertainty propagation
=======================

A short demonstration of how `UncertaintyQuantity` can be used to compute uncertainties. First
we'll import some essentials.
"""

import astropy.units as u
import numpy as np

from plasmapy.uncertainty import UncertaintyQuantity

######################################################
# First we define two `Quantities` with uncertainties and check their properties.

value0 = UncertaintyQuantity(30 * u.m, 5 * u.m)
value1 = UncertaintyQuantity(10 * u.m, 1 * u.m)

print("Value a = " + str(value0))

print("Base of a = " + str(value0.base()))

print("Uncertainty of a = " + str(value0.uncertainty))

print("Value b = " + str(value1))

print("Base of b = " + str(value1.base()))

print("Uncertainty of b = " + str(value1.uncertainty))

######################################################
# Next we can perform calculations with these `UncertaintyQuantity` variables like we would with
# normal or `Quantity` variables.

summation = value0 + value1
print("Summation (a + b) = " + str(summation))

subtraction = value0 - value1
print("Subtraction (a - b) = " + str(subtraction))

multiplication = value0 * value1
print("Multiplication (a * b) = " + str(multiplication))

division = value0 / value1
print("Division (a / b) = " + str(division))

power = (value0 / u.m) ** UncertaintyQuantity(2, 0.1)
print("Power ((a / [m]) ** (2 ± 0.1)) = " + str(power))

root = np.sqrt(value0)
print("Root (sqrt(a)) = " + str(root))
