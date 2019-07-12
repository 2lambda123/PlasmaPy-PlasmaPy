"""
Decorator for checking input/output arguments of functions.
"""
__all__ = ["check_values", "check_quantity", "check_relativistic",
           "CheckUnits", "CheckValues"]

import collections
import functools
import inspect
import numpy as np
import warnings

from astropy import units as u
from astropy.constants import c
from astropy.units import UnitsWarning
from astropy.units.core import _normalize_equivalencies
from astropy.units.decorators import _get_allowed_units
from plasmapy.utils.decorators import preserve_signature
from plasmapy.utils.exceptions import (PlasmaPyWarning,
                                       RelativityWarning,
                                       RelativityError)
from textwrap import dedent
from typing import (Any, Dict, List, Tuple, Union)


class CheckValues:
    """
    A decorator class to "check" -- limit/control -- the values of input
    arguments to a function.  (Checking of function arguments `*args` and
    `**kwargs` is not supported.)

    Parameters
    ----------
    **checks: Dict[str, Dict[str, bool]]
        Each keyword in `checks` is the name of the function argument to be
        checked and the keyword value is a dictionary specifying the limits on
        the function's argument value.  For example,
        `mass={'can_be_negative': False}` would specify the `mass` argument
        to a function can not be negative.  The following keys are allowed in
        the 'check' dictionary:

        ================ ======= ================================================
        Key              Type    Description
        ================ ======= ================================================
        can_be_negative  `bool`  `True` (DEFAULT) values can be negative
        can_be_complex   `bool`  `False` (DEFAULT) values can be complex numbers
        can_be_inf       `bool`  `True` (DEFAULT) values can be infinite
        can_be_nan       `bool`  `True` (DEFAULT) values can be NaN
        none_shall_pass  `bool`  `False` (DEFAULT) values can be python `None`
        ================ ======= ================================================

    Examples
    --------
    .. code-block:: python

        from plasmapy.utils.decorators import CheckValues
        @CheckValues(arg1={'can_be_negative': False, 'can_be_nan': False},
                     arg2={'can_be_inf': False})
        def foo(arg1, arg2):
            return arg1 + arg2

    Or the `**{}` notation can be utilized::

        from plasmapy.utils.decorators import CheckValues
        @CheckValues(**{'arg1': {'can_be_negative': False, 'can_be_nan': False},
                        'arg2': {'can_be_inf': False}})
        def foo(arg1, arg2):
            return arg1 + arg2
    """
    #: Default values for the possible 'check' keys.
    # To add a new check the the class, the following needs to be done:
    #   1. Add a key & default value to the `__check_defaults` dictionary
    #   2. Add a corresponding if-statement to method `_check_value`
    #
    __check_defaults = {
        'can_be_negative': True,
        'can_be_complex': False,
        'can_be_inf': True,
        'can_be_nan': True,
        'none_shall_pass': False,
    }

    def __init__(self, **checks: Dict[str, bool]):
        self._value_checks = checks

    def __call__(self, f):
        """
        Parameters
        ----------
        f
            Function to be wrapped/decorated.
        """
        self.f = f
        wrapped_sign = inspect.signature(f)

        @preserve_signature
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # combine args and kwargs into dictionary
            bound_args = wrapped_sign.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # get checks
            checks = self._get_value_checks(bound_args)

            # check argument values
            for arg_name in checks:
                self._check_value(bound_args.arguments[arg_name],
                                  arg_name,
                                  **checks[arg_name])

            return f(**bound_args.arguments)
        return wrapper

    def _get_value_checks(self,
                          bound_args: inspect.BoundArguments) -> Dict[str, Dict[str, bool]]:
        """
        Review function bound arguments and :attr:`value_checks` to build a complete 'value_checks'
        dictionary. Any unspecified check key is filled with a default value.

        Parameters
        ----------
        bound_args
            Bound Arguments passed to the function being wrapped.

        Returns
        -------
        Dict[str, Dict[str, bool]]
            A complete 'checks' dictionary for checking function input arguments.

        """
        # initialize validation dictionary
        out_checks = {}

        # Iterate through parameters, determine validation keys, and build checks
        # dictionary `out_checks`
        for param in bound_args.signature.parameters.values():
            # variable arguments are NOT checked
            # e.g. in foo(x, y, *args, d=None, **kwargs) variable arguments
            #      *args and **kwargs will NOT be checked
            #
            if param.kind in (inspect.Parameter.VAR_KEYWORD,
                              inspect.Parameter.VAR_POSITIONAL):
                continue

            # grab the checks dictionary for the desired parameter
            try:
                param_in_checks = self.value_checks[param.name]
            except KeyError:
                # checks for parameter not specified
                continue

            # build `out_checks`
            # read checks and/or apply defaults values
            out_checks[param.name] = {}
            for v_name, v_default in self.__check_defaults.items():
                out_checks[param.name][v_name] = \
                    param_in_checks.get(v_name, v_default)

        # Does `self.checks` indicate arguments not used by f?
        missing_params = [
            param
            for param in set(self.value_checks.keys()) - set(out_checks.keys())
        ]
        if len(missing_params) > 0:
            params_str = ", ".join(missing_params)
            warnings.warn(PlasmaPyWarning(
                f"Expected to value check parameters {params_str} but they "
                f"are missing from the call to {self.f.__name__}"))

        return out_checks

    def _check_value(self, arg, arg_name, **arg_checks: bool):
        """
        Perform requested argument checks.

        Parameters
        ----------
        arg
            The argument to be checked
        arg_name: str
            The name of the argument to be checked
        arg_checks: Dict[str, bool]
            The requested checks for the argument.

        Raises
        ------
        ValueError
            If a check fails, then `ValueError` is raised.

        """
        valueerror_msg = (f"The argument '{arg_name}'' to function "
                          f"{self.f.__name__}() can not contain")

        # check values
        if arg is None and arg_checks['none_shall_pass']:
            return
        elif arg is None:
            raise ValueError(f"{valueerror_msg} Nones.")
        elif not arg_checks['can_be_negative']:
            # Allow NaNs through without raising a warning
            with np.errstate(invalid='ignore'):
                isneg = np.any(arg < 0)
            if isneg:
                raise ValueError(f"{valueerror_msg} negative numbers.")
        elif not arg_checks['can_be_complex'] and np.any(np.iscomplexobj(arg)):
            raise ValueError(f"{valueerror_msg} complex numbers.")
        elif not arg_checks['can_be_inf'] and np.any(np.isinf(arg)):
            raise ValueError(f"{valueerror_msg} infs.")
        elif not arg_checks['can_be_nan'] and np.any(np.isnan(arg)):
            raise ValueError(f"{valueerror_msg} NaNs.")

    @property
    def value_checks(self) -> Dict[str, Dict[str, bool]]:
        """Dictionary of requested argument checks."""
        return self._value_checks


class CheckUnits:
    """
    A decorator class to "check" -- limit/control -- the units of input/output
    arguments to a function. (Checking of function arguments `*args` and `**kwargs`
    is not supported.)

    Parameters
    ----------
    **checks: Union[u.Unit, List[u.Unit], Dict[str, Any]]
        Each keyword in `checks` is the name of the function argument to be checked
        and the keyword value is either a list of desired astropy
        :class:`~astropy.units.Unit`'s or a dictionary specifying the desired unit
        checks.  The following keys are allowed in the `check` dictionary:

        ====================== ======= ================================================
        Key                    Type    Description
        ====================== ======= ================================================
        units                          list of desired astropy
                                       :class:`~astropy.units.Unit`'s
        equivalencies                  [DEFAULT `None`] A list of equivalent pairs to
                                       try if the units are not directly convertible.
                                       (see :mod:`~astropy.units.equivalencies` and/or
                                       `astropy equivalencies`_)
        pass_equivalent_units  `bool`  [DEFAULT `False`] allow equivalent units to pass
        ====================== ======= ================================================

    Notes
    -----
    * Decorator does NOT perform any unit conversions.
    * If it is desired that `None` values do not raise errors or warnings, then
      include `None` in the list of units.
    * If units are not specified in `checks`, then the decorator will attempt
      to identify desired units by examining the function annotations.

    Examples
    --------
    .. code-block:: python

        from plasmapy.utils.decorators import CheckUnits
        @CheckUnits(arg1={'units': u.cm}, arg2=u.cm)
        def foo(arg1, arg2):
            return arg1 + arg2

    Or the `**{}` notation can be utilized::

        from plasmapy.utils.decorators import CheckValues
        @CheckValues(**{'arg1': {'units': u.cm},
                        'arg2': u.cm})
        def foo(arg1, arg2):
            return arg1 + arg2

    .. _astropy equivalencies:
        https://docs.astropy.org/en/stable/units/equivalencies.html
    """
    #: Default values for the possible 'check' keys.
    # To add a new check the the class, the following needs to be done:
    #   1. Add a key & default value to the `__check_defaults` dictionary
    #   2. Add a corresponding conditioning statement to `_get_value_checks`
    #   3. Add a corresponding behavior to `_check_unit`
    #
    __check_defaults = {
        'units': None,
        'equivalencies': None,
        'pass_equivalent_units': False,
        'none_shall_pass': False,
    }

    def __init__(
            self,
            checks_on_return: Union[u.Unit,
                                    List[Union[u.Unit, None]],
                                    Dict[str, Any]] = None,
            **checks: Union[u.Unit, List[Union[u.Unit, None]], Dict[str, Any]]):
        self._unit_checks = checks

        if checks_on_return is not None:
            self._unit_checks['checks_on_return'] = checks_on_return

    def __call__(self, f):
        """
        Parameters
        ----------
        f
            Function to be wrapped/decorated.
        """
        self.f = f
        wrapped_sign = inspect.signature(f)

        @preserve_signature
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # combine args and kwargs into dictionary
            bound_args = wrapped_sign.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # get checks
            checks = self._get_unit_checks(bound_args)

            # check (input) argument units
            for arg_name in checks:
                # skip check of output/return
                if arg_name == 'checks_on_return':
                    continue

                # check argument
                self._check_unit(bound_args.arguments[arg_name],
                                 arg_name,
                                 **checks[arg_name])

            # call function
            _return = f(**bound_args.arguments)

            # check output
            if 'checks_on_return' in checks:
                self._check_unit(_return, 'checks_on_return',
                                 **checks['checks_on_return'])

            return _return
        return wrapper

    def _get_unit_checks(self,
                         bound_args: inspect.BoundArguments) -> Dict[str, Dict[str, Any]]:
        out_checks = {}

        # Iterate through function bound arguments + return and determine check keys:
        #   1. 'units'
        #   2. 'equivalencies'
        #   3. 'pass_equivalent_units'
        #
        # artificially add "return" to parameters
        things_to_check = bound_args.signature.parameters.copy()
        things_to_check['checks_on_return'] = \
            inspect.Parameter('checks_on_return',
                              inspect.Parameter.POSITIONAL_ONLY,
                              annotation=bound_args.signature.return_annotation)
        for param in things_to_check.values():
            # variable arguments are NOT checked
            # e.g. in foo(x, y, *args, d=None, **kwargs) variable arguments
            #      *args and **kwargs will NOT be checked
            #
            if param.kind in (inspect.Parameter.VAR_KEYWORD,
                              inspect.Parameter.VAR_POSITIONAL):
                continue

            # grab the checks dictionary for the desired parameter
            try:
                param_checks = self.unit_checks[param.name]
            except KeyError:
                param_checks = None

            # -- Determine target units `_units` --
            # target units can be define in one of three ways (in
            # preferential order):
            #   1. direct keyword pass-through
            #      i.e. CheckUnits(x=u.cm)
            #           CheckUnits(x=[u.cm, u.s])
            #   2. keyword pass-through via dictionary definition
            #      i.e. CheckUnits(x={'units': u.cm})
            #           CheckUnits(x={'units': [u.cm, u.s]})
            #   3. function annotations
            #
            # * options (1) and (2) will supersede option (3)
            # * if None is included in the units list, then None values are allowed
            #
            _none_shall_pass = False
            _units = None
            if param_checks is not None:
                # checks for argument were defined with decorator
                try:
                    _units = param_checks['units']
                except TypeError:
                    # if checks is NOT None and is NOT a dictionary, then assume
                    # only units were specified
                    #   e.g. CheckUnits(x=u.cm)
                    #
                    _units = param_checks
                except KeyError:
                    # if checks does NOT have 'units' but is still a dictionary,
                    # then other check conditions may have been specified and the
                    # user is relying on function annotations to define desired
                    # units
                    _units = None

            # If no units have been specified by decorator checks, then look for
            # function annotations.
            if _units is None:
                _units = param.annotation

                if _units is not inspect.Parameter.empty:
                    # unit annotations defined
                    pass
                elif param_checks is None:
                    # no checks specified and no unit annotations defined
                    continue
                else:
                    raise ValueError(
                        f"No astropy.units specified for argument {param.name} "
                        f"of function {self.f.__name__}.")

            # Ensure `_units` is an iterable
            if not isinstance(_units, collections.abc.Iterable):
                # target units/physical types is singular
                _units = [_units]

            # Is None allowed?
            if None in _units or param.default is None:
                _none_shall_pass = True

            # Remove Nones
            if None in _units:
                _units = [t for t in _units if t is not None]

            # ensure all _units are astropy.units.Unit or physical types &
            # define 'units' for unit checks &
            # define 'none_shall_pass' check
            _units = self._condition_target_units(_units)
            out_checks[param.name] = {'units': _units,
                                      'none_shall_pass': _none_shall_pass}

            # -- Determine target equivalencies --
            # Unit equivalences can be defined by:
            # 1. keyword pass-through via dictionary definition
            #    e.g. CheckUnits(x={'units': u.C,
            #                       'equivalencies': u.temperature})
            #
            # initialize equivalencies
            try:
                _equivs = param_checks['equivalencies']
            except (KeyError, TypeError):
                _equivs = self.__check_defaults['equivalencies']

            # ensure equivalences are properly formatted
            if _equivs is None:
                _equivs = [None] * len(_units)
            elif isinstance(_equivs, list):
                if all(isinstance(el, tuple) for el in _equivs):
                    _equivs = [_equivs]

                # ensure passed equivalencies list is structured properly
                #   [[(), ...], ...]
                #
                # * All equivalencies must be a list of 2, 3, or 4 element tuples
                #   structured like...
                #     (from_unit, to_unit, forward_func, backward_func)
                #
                norm_equivs = []
                for equiv in _equivs:
                    norm_equivs.append(self._normalize_equivalencies(equiv))
                _equivs = norm_equivs

                # ensure number of equivalencies lists match the number of
                # equivalent units to check
                if len(_equivs) == 1:
                    _equivs = _equivs * len(_units)
                elif len(_equivs) != len(_units):
                    raise ValueError(
                        f"The length of the specified equivalencies list "
                        f"({len(_equivs)}) must be 1 or equal to the "
                        f"number of specified units ({len(_units)})")

            out_checks[param.name]['equivalencies'] = _equivs

            # -- Determine if equivalent units pass --
            try:
                peu = param_checks.get(
                    'pass_equivalent_units',
                    self.__check_defaults['pass_equivalent_units']
                )
            except (AttributeError, TypeError):
                peu = self.__check_defaults['pass_equivalent_units']

            out_checks[param.name]['pass_equivalent_units'] = peu

        # Does `self.unit_checks` indicate arguments not used by f?
        missing_params = [
            param
            for param in set(self.unit_checks.keys()) - set(out_checks.keys())
        ]
        if len(missing_params) > 0:
            params_str = ", ".join(missing_params)
            warnings.warn(PlasmaPyWarning(
                f"Expected to unit check parameters {params_str} but they "
                f"are missing from the call to {self.f.__name__}"))

        return out_checks

    def _check_unit(self,
                    arg,
                    arg_name,
                    **arg_checks: Union[List, None, bool]) -> Tuple[Any, Any, Any]:

        # initialize ValueError message
        valueerror_msg = (f"The argument {arg_name} to function "
                          f"{self.f.__name__} can not contain")

        # initialize TypeError message
        typeerror_msg = (
            f"The argument {arg_name} to {self.f.__name__} should "
            f"be an astropy Quantity with "
        )
        if len(arg_checks['units']) == 1:
            typeerror_msg += f"the following unit: {arg_checks['units'][0]}"
        else:
            typeerror_msg += "one of the following units: "
            for unit in arg_checks['units']:
                typeerror_msg += str(unit)
                if unit != arg_checks['units'][-1]:
                    typeerror_msg += ", "
        if arg_checks['none_shall_pass']:
            typeerror_msg += "or None "

        # pass Nones if allowed
        if arg is None:
            if arg_checks['none_shall_pass']:
                return arg, None, None
            else:
                raise ValueError(f"{valueerror_msg} Nones")

        # check units
        in_acceptable_units = []
        for unit, equiv in zip(arg_checks['units'], arg_checks['equivalencies']):
            try:
                in_acceptable_units.append(
                    arg.unit.is_equivalent(unit, equivalencies=equiv)
                )
            except AttributeError:
                if hasattr(arg, 'unit'):
                    err_msg = "a 'unit' attribute without an 'is_equivalent' method"
                else:
                    err_msg = "no 'unit' attribute"

                raise TypeError(f"Argument {arg_name} to function {self.f.__name__}"
                                f" has {err_msg}. Pass in an astropy Quantity instead.")

        # How many acceptable units?
        nacceptable = np.count_nonzero(in_acceptable_units)
        if nacceptable == 0:
            # NO equivalent units
            raise u.UnitTypeError(typeerror_msg)
        else:
            # is there an exact match?
            units_arr = np.array(arg_checks['units'])
            units_equal_mask = np.equal(units_arr, arg.unit)
            units_mask = np.logical_and(units_equal_mask, in_acceptable_units)
            if np.count_nonzero(units_mask) == 1:
                # matched exactly to a desired unit
                unit = units_arr[units_mask]
                equiv = np.array(arg_checks['equivalencies'])[units_mask]

                return arg, unit[0], equiv[0]
            else:
                if arg_checks['pass_equivalent_units']:
                    return arg, None, None
                else:
                    raise u.UnitTypeError(typeerror_msg)

    @staticmethod
    def _condition_target_units(targets):
        """
        From a list of target units (either as a string or unit
        objects) and physical types, return a list of
        :class:`astropy.units.Unit` objects.
        (see :func:`astropy.units.decorators._get_allowed_units`)
        """
        return _get_allowed_units(targets)

    @staticmethod
    def _normalize_equivalencies(equivalencies):
        """
        Normalizes equivalencies to ensure each is in a 4-tuple form::

            (from_unit, to_unit, forward_func, backward_func)

        Parameters
        ----------
        equivalencies: list of equivalent pairs


        Notes
        -----
        * see astropy function :func:`~astropy.units.core._normalize_equivalencies`
        """
        return _normalize_equivalencies(equivalencies)

    @property
    def unit_checks(self) -> Dict[str, Dict[str, Any]]:
        """Dictionary of requested argument checks."""
        return self._unit_checks


def check_units(func=None, **checks: Dict[str, Any]):
    """
    A decorator to "check" -- limit/control -- the units of input/output
    arguments to a function. (Checking of function arguments `*args` and `**kwargs`
    is not supported.)

    Parameters
    ----------
    func:
        The function to be decorated

    **checks: Union[u.Unit, List[u.Unit], Dict[str, Any]]
        Each keyword in `checks` is the name of the function argument to be checked
        and the keyword value is either a list of desired astropy
        :class:`~astropy.units.Unit`'s or a dictionary specifying the desired unit
        checks.  The following keys are allowed in the `check` dictionary:

        ====================== ======= ================================================
        Key                    Type    Description
        ====================== ======= ================================================
        units                          list of desired astropy
                                       :class:`~astropy.units.Unit`'s
        equivalencies                  [DEFAULT `None`] A list of equivalent pairs to
                                       try if the units are not directly convertible.
                                       (see :mod:`~astropy.units.equivalencies` and/or
                                       `astropy equivalencies`_)
        pass_equivalent_units  `bool`  [DEFAULT `False`] allow equivalent units to pass
        ====================== ======= ================================================

    Notes
    -----
    * Decorator does NOT perform any unit conversions.
    * If it is desired that `None` values do not raise errors or warnings, then
      include `None` in the list of units.
    * If units are not specified in `checks`, then the decorator will attempt
      to identify desired units by examining the function annotations.

    Examples
    --------
    .. code-block:: python

        from plasmapy.utils.decorators import check_values
        @check_values(arg1={'can_be_negative': False, 'can_be_nan': False},
                      arg2={'can_be_inf': False})
        def foo(arg1, arg2):
            return arg1 + arg2

    Or the `**{}` notation can be utilized::

        from plasmapy.utils.decorators import check_values
        @check_values(**{'arg1': {'can_be_negative': False, 'can_be_nan': False},
                         'arg2': {'can_be_inf': False}})
        def foo(arg1, arg2):
            return arg1 + arg2

    .. _astropy equivalencies:
        https://docs.astropy.org/en/stable/units/equivalencies.html
    """
    if func is not None:
        return CheckUnits(**checks)(func)
    else:
        return CheckUnits(**checks)


def check_values(func=None, **checks: Dict[str, bool]):
    """
    A decorator to "check" -- limit/control -- values of input arguments to a
    function.  (Checking of function arguments `*args` and `**kwargs` is not
    supported.)

    Parameters
    ----------
    func:
        The function to be decorated

    **checks: Dict[str, Dict[str, bool]]
        Each keyword in `checks` is the name of the function argument to be checked
        and the keyword value is a dictionary specifying the limits on the function's
        argument value.  For example, `mass={'can_be_negative': False}` would
        specify the `mass` argument to a function can not be negative.  The
        following keys are allowed in the 'check' dictionary:

        ================ ======= ================================================
        Key              Type    Description
        ================ ======= ================================================
        can_be_negative  `bool`  `True` (DEFAULT) values can be negative
        can_be_complex   `bool`  `False` (DEFAULT) values can be complex numbers
        can_be_inf       `bool`  `True` (DEFAULT) values can be infinite
        can_be_nan       `bool`  `True` (DEFAULT) values can be NaN
        none_shall_pass  `bool`  `False` (DEFAULT) values can be python `None`
        ================ ======= ================================================

    Notes
    -----
    * Full functionality is defined by the class :class:`CheckValues`.

    Examples
    --------
    .. code-block:: python

        from plasmapy.utils.decorators import check_values
        @check_values(arg1={'can_be_negative': False, 'can_be_nan': False},
                      arg2={'can_be_inf': False})
        def foo(arg1, arg2):
            return arg1 + arg2

    Or the `**{}` notation can be utilized::

        from plasmapy.utils.decorators import check_values
        @check_values(**{'arg1': {'can_be_negative': False, 'can_be_nan': False},
                         'arg2': {'can_be_inf': False}})
        def foo(arg1, arg2):
            return arg1 + arg2
    """
    if func is not None:
        return CheckValues(**checks)(func)
    else:
        return CheckValues(**checks)


def check_quantity(**validations: Dict[str, Union[bool, u.Quantity]]):
    """
    Verify that the function's arguments have correct units.

    This decorator raises an exception if an annotated argument in the
    decorated function is an `~astropy.units.Quantity` with incorrect units
    or of incorrect kind. You can prevent arguments from being input as
    Nones, NaNs, negatives, infinities and complex numbers.

    If a number (non-Quantity) value is inserted in place of a value with units,
    assume the input is an SI Quantity and cast it to one.

    This is probably best illustrated with an example:

    Examples
    --------
    >>> from astropy import units as u
    >>> @check_quantity(x={"units": u.m,
    ...       "can_be_negative": False,
    ...       "can_be_complex": True,
    ...       "can_be_inf": True})
    ... def func(x):
    ...     return x

    >>> func(1 * u.m)
    <Quantity 1. m>

    >>> func(1 * u.s)
    Traceback (most recent call last):
      ...
    astropy.units.core.UnitConversionError: The argument x to func should be a Quantity with the following units: m

    >>> import pytest    # to show the UnitsWarning
    >>> with pytest.warns(u.UnitsWarning, match="Assuming units of m."):
    ...     func(1)
    <Quantity 1. m>

    >>> func(-1 * u.m)
    Traceback (most recent call last):
      ...
    ValueError: The argument x to function func cannot contain negative numbers.

    >>> func(np.inf * u.m)
    <Quantity inf m>

    >>> func(None)
    Traceback (most recent call last):
      ...
    ValueError: The argument x to function func cannot contain Nones.

    Parameters
    ----------
    dict
        Arguments to be validated passed in as keyword arguments, with values as
        validation dictionaries, with structure as in the example.  Valid keys for
        each argument are:
        'units': `astropy.units.Unit`,
        'can_be_negative': `bool`,
        'can_be_complex': `bool`,
        'can_be_inf': `bool`,
        'can_be_nan': `bool`,
        'none_shall_pass': `bool`

    Raises
    ------
    `TypeError`
        If the argument is not a `~astropy.units.Quantity`, units is not
        entirely units or `argname` does not have a type annotation.

    `~astropy.units.UnitConversionError`
        If the argument is not in acceptable units.

    `~astropy.units.UnitsError`
        If after the assumption checks, the argument is still not in acceptable
        units.

    `ValueError`
        If the argument contains `~numpy.nan` or other invalid values as
        determined by the keywords.

    Warns
    -----
    `~astropy.units.UnitsWarning`
        If a `~astropy.units.Quantity` is not provided and unique units
        are provided, a `UnitsWarning` will be raised and the inputted
        units will be assumed.

    Notes
    -----
    This functionality may end up becoming deprecated due to
    noncompliance with the `IEEE 754 standard
    <https://en.wikipedia.org/wiki/IEEE_754#Exception_handling>`_
    and in favor of `~astropy.units.quantity_input`.

    Returns
    -------
    function
        Decorated function.

    See also
    --------
    _check_quantity

    """
    def decorator(f):
        wrapped_sign = inspect.signature(f)
        fname = f.__name__

        @preserve_signature
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # combine args and kwargs into dictionary
            bound_args = wrapped_sign.bind(*args, **kwargs)
            bound_args.apply_defaults()
            given_params_values = bound_args.arguments
            given_params = set(given_params_values.keys())

            # names of params to check
            validated_params = set(validations.keys())

            missing_params = [
                param for param in (validated_params - given_params)
            ]

            if len(missing_params) > 0:
                params_str = ", ".join(missing_params)
                raise TypeError(
                    f"Call to {fname} is missing "
                    f"validated params {params_str}")

            for param_to_check, validation_settings in validations.items():
                value_to_check = given_params_values[param_to_check]

                can_be_negative = validation_settings.get('can_be_negative', True)
                can_be_complex = validation_settings.get('can_be_complex', False)
                can_be_inf = validation_settings.get('can_be_inf', True)
                can_be_nan = validation_settings.get('can_be_nan', True)
                none_shall_pass = validation_settings.get('none_shall_pass', False)

                validated_value = _check_quantity(value_to_check,
                                                  param_to_check,
                                                  fname,
                                                  validation_settings['units'],
                                                  can_be_negative=can_be_negative,
                                                  can_be_complex=can_be_complex,
                                                  can_be_inf=can_be_inf,
                                                  can_be_nan=can_be_nan,
                                                  none_shall_pass=none_shall_pass)
                given_params_values[param_to_check] = validated_value

            return f(**given_params_values)

        return wrapper
    return decorator


def _check_quantity(arg, argname, funcname, units, can_be_negative=True,
                    can_be_complex=False, can_be_inf=True, can_be_nan=True,
                    none_shall_pass=False):
    """
    Raise an exception if an object is not a `~astropy.units.Quantity`
    with correct units and valid numerical values.

    Parameters
    ----------
    arg : ~astropy.units.Quantity
        The object to be tested.

    argname : str
        The name of the argument to be printed in error messages.

    funcname : str
        The name of the original function to be printed in error messages.

    units : `~astropy.units.Unit` or list of `~astropy.unit.Unit`
        Acceptable units for `arg`.

    can_be_negative : bool, optional
        `True` if the `~astropy.units.Quantity` can be negative,
        `False` otherwise.  Defaults to `True`.

    can_be_complex : bool, optional
        `True` if the `~astropy.units.Quantity` can be a complex number,
        `False` otherwise.  Defaults to `False`.

    can_be_inf : bool, optional
        `True` if the `~astropy.units.Quantity` can contain infinite
        values, `False` otherwise.  Defaults to `True`.

    can_be_nan : bool, optional
        `True` if the `~astropy.units.Quantity` can contain NaN
        values, `False` otherwise.  Defaults to `True`.

    none_shall_pass : bool, optional
        `True` if the `~astropy.units.Quantity` can contain None
        values, `False` otherwise.  Defaults to `True`.

    Raises
    ------
    TypeError
        If the argument is not a `~astropy.units.Quantity` or units is
        not entirely units.

    ~astropy.units.UnitConversionError
        If the argument is not in acceptable units.

    ~astropy.units.UnitsError
        If after the assumption checks, the argument is still not in acceptable
        units.

    ValueError
        If the argument contains any `~numpy.nan` or other invalid
        values as determined by the keywords.

    Warns
    -----
    ~astropy.units.UnitsWarning
        If a `~astropy.units.Quantity` is not provided and unique units
        are provided, a `UnitsWarning` will be raised and the inputted
        units will be assumed.

    Examples
    --------
    >>> from astropy import units as u
    >>> import pytest
    >>> _check_quantity(4*u.T, 'B', 'f', u.T)
    <Quantity 4. T>
    >>> with pytest.warns(u.UnitsWarning, match="No units are specified"):
    ...     assert _check_quantity(4, 'B', 'f', u.T) == 4 * u.T

    """

    # TODO: Replace `funcname` with func.__name__?

    if not isinstance(units, list):
        units = [units]

    for unit in units:
        if not isinstance(unit, (u.Unit, u.CompositeUnit, u.IrreducibleUnit)):
            raise TypeError(
                "The keyword 'units' to check_quantity must be "
                "a unit or a list/tuple containing only units.")

    # Create a generic error message

    typeerror_message = (
        f"The argument {argname} to {funcname} should be a Quantity with "
    )

    if len(units) == 1:
        typeerror_message += f"the following units: {str(units[0])}"
    else:
        typeerror_message += "one of the following units: "
        for unit in units:
            typeerror_message += str(unit)
            if unit != units[-1]:
                typeerror_message += ", "
    if none_shall_pass:
        typeerror_message += "or None "

    if isinstance(arg, (u.Unit, u.CompositeUnit, u.IrreducibleUnit)):
        raise TypeError(typeerror_message)

    # Make sure arg is a quantity with correct units

    unit_casting_warning = dedent(
            f"""No units are specified for {argname} = {arg} in {funcname}. Assuming units of {str(units[0])}.
                To silence this warning, explicitly pass in an Astropy Quantity (from astropy.units)
                (see http://docs.astropy.org/en/stable/units/)""")

    # TODO include explicit note on how to pass in Astropy Quantity

    valueerror_message = (
        f"The argument {argname} to function {funcname} cannot contain"
    )

    if arg is None and none_shall_pass:
        return arg
    elif arg is None:
        raise ValueError(f"{valueerror_message} Nones.")
    if not isinstance(arg, (u.Quantity)):
        if len(units) != 1:
            raise TypeError(typeerror_message)
        else:
            try:
                arg = arg * units[0]
            except (u.UnitsError, ValueError):
                raise TypeError(typeerror_message)
            else:
                warnings.warn(UnitsWarning(unit_casting_warning))
    if not isinstance(arg, u.Quantity):
        raise u.UnitsError("{} is still not a Quantity after checks!".format(arg))

    in_acceptable_units = []

    for unit in units:
        try:
            arg.unit.to(unit, equivalencies=u.temperature_energy())
        except Exception:
            in_acceptable_units.append(False)
        else:
            in_acceptable_units.append(True)

    if not np.any(in_acceptable_units):
        raise u.UnitConversionError(typeerror_message)

    # Make sure that the quantity has valid numerical values
    if np.any(np.isnan(arg.value)) and not can_be_nan:
        raise ValueError(f"{valueerror_message} NaNs.")
    elif np.any(np.iscomplex(arg.value)) and not can_be_complex:
        raise ValueError(f"{valueerror_message} complex numbers.")
    elif not can_be_negative:
        # Allow NaNs through without raising a warning
        with np.errstate(invalid='ignore'):
            isneg = np.any(arg.value < 0)
        if isneg:
            raise ValueError(f"{valueerror_message} negative numbers.")
    elif not can_be_inf and np.any(np.isinf(arg.value)):
        raise ValueError(f"{valueerror_message} infs.")

    return arg


def check_relativistic(func=None, betafrac=0.05):
    r"""
    Warns or raises an exception when the output of the decorated
    function is greater than `betafrac` times the speed of light.

    Parameters
    ----------
    func : `function`, optional
        The function to decorate.

    betafrac : float, optional
        The minimum fraction of the speed of light that will raise a
        `~plasmapy.utils.RelativityWarning`. Defaults to 5%.

    Returns
    -------
    function
        Decorated function.

    Raises
    ------
    TypeError
        If `V` is not a `~astropy.units.Quantity`.

    ~astropy.units.UnitConversionError
        If `V` is not in units of velocity.

    ValueError
        If `V` contains any `~numpy.nan` values.

    ~plasmapy.utils.RelativityError
        If `V` is greater than or equal to the speed of light.

    Warns
    -----
    ~plasmapy.utils.RelativityWarning
        If `V` is greater than or equal to `betafrac` times the speed of light,
        but less than the speed of light.

    Examples
    --------
    >>> from astropy import units as u
    >>> @check_relativistic
    ... def speed():
    ...     return 1 * u.m / u.s

    Passing in a custom `betafrac`:

    >>> @check_relativistic(betafrac=0.01)
    ... def speed():
    ...     return 1 * u.m / u.s

    """
    def decorator(f):

        @preserve_signature
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return_ = f(*args, **kwargs)
            _check_relativistic(return_, f.__name__, betafrac=betafrac)
            return return_

        return wrapper
    if func:
        return decorator(func)
    return decorator


def _check_relativistic(V, funcname, betafrac=0.05):
    r"""
    Warn or raise error for relativistic or superrelativistic
    velocities.

    Parameters
    ----------
    V : ~astropy.units.Quantity
        A velocity.

    funcname : str
        The name of the original function to be printed in the error
        messages.

    betafrac : float, optional
        The minimum fraction of the speed of light that will generate
        a warning. Defaults to 5%.

    Raises
    ------
    TypeError
        If `V` is not a `~astropy.units.Quantity`.

    ~astropy.units.UnitConversionError
        If `V` is not in units of velocity.

    ValueError
        If `V` contains any `~numpy.nan` values.

    RelativityError
        If `V` is greater than or equal to the speed of light.

    Warns
    -----
    ~plasmapy.utils.RelativityWarning
        If `V` is greater than or equal to the specified fraction of the
        speed of light.

    Examples
    --------
    >>> from astropy import units as u
    >>> _check_relativistic(1*u.m/u.s, 'function_calling_this')

    """

    # TODO: Replace `funcname` with func.__name__?

    errmsg = ("V must be a Quantity with units of velocity in"
              "_check_relativistic")

    if not isinstance(V, u.Quantity):
        raise TypeError(errmsg)

    try:
        V_over_c = (V / c).to_value(u.dimensionless_unscaled)
    except Exception:
        raise u.UnitConversionError(errmsg)

    beta = np.max(np.abs((V_over_c)))

    if beta == np.inf:
        raise RelativityError(f"{funcname} is yielding an infinite velocity.")
    elif beta >= 1:
        raise RelativityError(
            f"{funcname} is yielding a velocity that is {str(round(beta, 3))} "
            f"times the speed of light.")
    elif beta >= betafrac:
        warnings.warn(
            f"{funcname} is yielding a velocity that is "
            f"{str(round(beta * 100, 3))}% of the speed of "
            f"light. Relativistic effects may be important.",
            RelativityWarning)
