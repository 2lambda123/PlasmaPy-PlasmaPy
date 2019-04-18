"""Exceptions and warnings specific to PlasmaPy."""


# ----------
# Exceptions
# ----------

class PlasmaPyError(Exception):
    """
    Base class of PlasmaPy custom errors.

    All custom exceptions raised by PlasmaPy should inherit from this
    class and be defined in this module.
    """
    pass


class PhysicsError(PlasmaPyError, ValueError):
    """
    The base exception for physics-related errors.
    """
    pass


class RelativityError(PhysicsError):
    """
    An exception for speeds greater than the speed of light.
    """
    pass


class DataStandardError(PlasmaPyError):
    """An exception for when HDF5 is not defined by OpenPMD standard."""
    pass


# ----------
# Warnings:
# ----------

class PlasmaPyWarning(Warning):
    """
    Base class of PlasmaPy custom warnings.

    All PlasmaPy custom warnings should inherit from this class and be
    defined in this module.

    Warnings should be issued using `~warnings.warn`, which will not break
    execution if unhandled.

    """
    pass


class PhysicsWarning(PlasmaPyWarning):
    """The base warning for `~plasmapy.physics` related warnings."""
    pass


class RelativityWarning(PhysicsWarning):
    """
    A warning for when relativistic velocities are being used in or are
    returned by non-relativistic functionality.
    """
    pass


class CouplingWarning(PhysicsWarning):
    """
    A warning for functions that rely on a particular coupling regime to be valid.
    """


