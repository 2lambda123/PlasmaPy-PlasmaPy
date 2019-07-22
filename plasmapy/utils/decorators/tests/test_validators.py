"""
Tests for 'validate` decorators (i.e. decorators that check objects and change them
when possible).
"""
import inspect
import pytest

from astropy import units as u
from plasmapy.utils.decorators.checks import (CheckUnits, CheckValues)
from plasmapy.utils.decorators.validators import (validate_quantities,
                                                  ValidateQuantities)
from plasmapy.utils.exceptions import ImplicitUnitConversionWarning
from typing import (Any, Dict)
from unittest import mock


# ----------------------------------------------------------------------------------------
# Test Decorator class `ValidateQuantities` and decorator `validate_quantities`
# ----------------------------------------------------------------------------------------
class TestValidateQuantities:
    """
    Test for decorator
    :class:`~plasmapy.utils.decorators.validators.validate_quantities` and decorator
    class :class:`~plasmapy.utils.decorators.validators.ValidateQuantities`.
    """

    unit_check_defaults = CheckUnits._CheckUnits__check_defaults  # type: Dict[str, Any]
    value_check_defaults = CheckValues._CheckValues__check_defaults  # type: Dict[str, Any]
    check_defaults = {**unit_check_defaults, **value_check_defaults}

    @staticmethod
    def foo(x):
        return x

    @staticmethod
    def foo_anno(x: u.cm):
        return x

    def test_inheritance(self):
        assert issubclass(ValidateQuantities, CheckUnits)
        assert issubclass(ValidateQuantities, CheckValues)

    def test_vq_method__get_validations(self):
        # method must exist
        assert hasattr(ValidateQuantities, 'validations')
        assert hasattr(ValidateQuantities, '_get_validations')

        # setup default validations
        default_validations = self.check_defaults.copy()
        default_validations['units'] = [default_validations.pop('units')]
        default_validations['equivalencies'] = [default_validations.pop('equivalencies')]

        # setup test cases
        # 'setup' = arguments for `_get_validations`
        # 'output' = expected return from `_get_validations`
        # 'raises' = if `_get_validations` raises an Exception
        # 'warns' = if `_get_validations` issues a warning
        #
        _cases = [
            # typical call
            {'setup': {'function': self.foo,
                       'args': (5, ),
                       'kwargs': {},
                       'validations': {'x': {'units': u.cm, 'can_be_negative': False}},
                       },
             'output': {'x': {'units': [u.cm],
                              'can_be_negative': False}},
             },
            {'setup': {'function': self.foo,
                       'args': (5,),
                       'kwargs': {},
                       'validations': {'x': {'units': u.cm, 'none_shall_pass': True}},
                       },
             'output': {'x': {'units': [u.cm],
                              'none_shall_pass': True}},
             },

            # call w/o value validations
            {'setup': {'function': self.foo,
                       'args': (5,),
                       'kwargs': {},
                       'validations': {'x': {'units': u.cm}},
                       },
             'output': {'x': {'units': [u.cm]}},
             },

            # call w/o unit validations
            {'setup': {'function': self.foo,
                       'args': (5,),
                       'kwargs': {},
                       'validations': {'x': {'can_be_inf': False}},
                       },
             'raises': ValueError,
             },

            # 'none_shall_pass' defined w/ validations
            {'setup': {'function': self.foo,
                       'args': (5,),
                       'kwargs': {},
                       'validations': {'x': {'units': [u.cm, None]}},
                       },
             'output': {'x': {'units': [u.cm],
                              'none_shall_pass': True}},
             },

            # units are defined via function annotations
            {'setup': {'function': self.foo_anno,
                       'args': (5,),
                       'kwargs': {},
                       'validations': {},
                       },
             'output': {'x': {'units': [u.cm]}},
             },

            # define 'validations_on_return'
            {'setup': {'function': self.foo,
                       'args': (5,),
                       'kwargs': {},
                       'validations': {'validations_on_return': {'units': [u.cm, None]}},
                       },
             'output': {'validations_on_return': {'units': [u.cm],
                                                  'none_shall_pass': True}},
             },
        ]

        for case in _cases:
            sig = inspect.signature(case['setup']['function'])
            args = case['setup']['args']
            kwargs = case['setup']['kwargs']
            bound_args = sig.bind(*args, **kwargs)

            vq = ValidateQuantities(**case['setup']['validations'])
            vq.f = case['setup']['function']
            if 'warns' in case:
                with pytest.warns(case['warns']):
                    validations = vq._get_validations(bound_args)
            elif 'raises' in case:
                with pytest.raises(case['raises']):
                    vq._get_validations(bound_args)
                continue
            else:
                validations = vq._get_validations(bound_args)

            # only expected argument validations exist
            assert sorted(validations.keys()) == sorted(case['output'].keys())

            # if validation key-value not specified then default is assumed
            for arg_name in case['output'].keys():
                arg_validations = validations[arg_name]

                for key in default_validations.keys():
                    if key in case['output'][arg_name]:
                        val = case['output'][arg_name][key]
                    else:
                        val = default_validations[key]

                    assert arg_validations[key] == val

        # method calls `_get_unit_checks` and `_get_value_checks`
        with mock.patch.object(CheckUnits,
                               '_get_unit_checks',
                               return_value={}) as mock_cu_get, \
                mock.patch.object(CheckValues,
                                  '_get_value_checks',
                                  return_value={}) as mock_cv_get:
            vq = ValidateQuantities(x=u.cm)
            vq.f = self.foo
            sig = inspect.signature(self.foo)
            bound_args = sig.bind(5)

            assert vq._get_validations(bound_args) == {}
            assert mock_cu_get.called
            assert mock_cv_get.called

    def test_vq_method__validate_quantity(self):

        # method must exist
        assert hasattr(ValidateQuantities, '_validate_quantity')

        # setup default validations
        default_validations = self.check_defaults.copy()
        default_validations['units'] = [default_validations.pop('units')]
        default_validations['equivalencies'] = [default_validations.pop('equivalencies')]

        # setup test cases
        # 'setup' = arguments for `_get_validations`
        # 'output' = expected return from `_get_validations`
        # 'raises' = if `_get_validations` raises an Exception
        # 'warns' = if `_get_validations` issues a warning
        #
        _cases = [
            # typical call
            {'input': {'args': (5 * u.cm, 'arg'),
                       'validations': {**default_validations,
                                       'units': [u.cm]}},
             'output': 5 * u.cm},

            # argument does not have units, but only one is specified
            {'input': {'args': (5, 'arg'),
                       'validations': {**default_validations,
                                       'units': [u.cm]}},
             'output': 5 * u.cm,
             'warns': u.UnitsWarning},

            # argument does not have units and multiple unit validations specified
            {'input': {'args': (5, 'arg'),
                       'validations': {**default_validations,
                                       'units': [u.cm, u.km],
                                       'equivalencies': [None, None]}},
             'raises': TypeError},

            # units can NOT be applied to argument
            {'input': {'args': ({}, 'arg'),
                       'validations': {**default_validations,
                                       'units': [u.cm]}},
             'raises': TypeError},

            # argument has a non-standard unit conversion
            {'input': {'args': (5. * u.K, 'arg'),
                       'validations': {**default_validations,
                                       'units': [u.eV],
                                       'equivalencies': [u.temperature_energy()]}},
             'output': (5. * u.K).to(u.eV, equivalencies=u.temperature_energy()),
             'warns': ImplicitUnitConversionWarning},

            # return value is None and not allowed
            {'input': {'args': (None, 'validations_on_return'),
                       'validations': {**default_validations,
                                       'units': [u.cm],
                                       'none_shall_pass': False}},
             'raises': ValueError},
        ]

        # setup wrapped function
        vq = ValidateQuantities()
        vq.f = self.foo

        # perform tests
        for case in _cases:
            arg, arg_name = case['input']['args']
            validations = case['input']['validations']

            if 'warns' in case:
                with pytest.warns(case['warns']):
                    _result = vq._validate_quantity(arg, arg_name, **validations)
            elif 'raises' in case:
                with pytest.raises(case['raises']):
                    vq._validate_quantity(arg, arg_name, **validations)
                continue
            else:
                _result = vq._validate_quantity(arg, arg_name, **validations)

            assert _result == case['output']

        # method calls `_check_unit_core` and `_check_value`
        case = {'input': (5. * u.cm, u.cm, {**default_validations, 'units': [u.cm]}),
                'output': 5. * u.cm}
        with mock.patch.object(CheckUnits,
                               '_check_unit_core',
                               return_value=(5*u.cm, u.cm, None, None)) \
                as mock_cu_checks, \
                mock.patch.object(CheckValues,
                                  '_check_value',
                                  return_value=None) as mock_cv_checks:

            args = case['input'][0:2]
            validations = case['input'][2]

            vq = ValidateQuantities(**validations)
            vq.f = self.foo

            assert vq._validate_quantity(*args, **validations) == case['output']
            assert mock_cu_checks.called
            assert mock_cv_checks.called

    def test_vq_preserves_signature(self):
        """Test `ValidateQuantities` preserves signature of wrapped function."""
        # I'd like to directly dest the @preserve_signature is used (??)

        wfoo = ValidateQuantities()(self.foo_anno)
        assert hasattr(wfoo, '__signature__')
        assert wfoo.__signature__ == inspect.signature(self.foo_anno)

