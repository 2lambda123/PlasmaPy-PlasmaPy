"""
Decorator to convert units of functions in /physics methods
"""
__all__ = ["angular_freq_to_hz"]

from astropy import units as u
from plasmapy.utils.decorators import preserve_signature


def angular_freq_to_hz(fn):
    def wrapper(*args, to_hz=False, **kwargs):
        _result = fn(*args, **kwargs)
        if to_hz:
            return _result.to(u.Hz, equivalencies=[(u.cy/u.s, u.Hz)])
        return _result
    return wrapper
