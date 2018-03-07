import pytest
import numpy as np
from itertools import product
from astropy import units as u, constants as const

from ..symbols import (
    atomic_symbol,
    isotope_symbol,
    element_name,
)

from ..isotopes import _Isotopes

from ..atomic import (
    atomic_number,
    mass_number,
    standard_atomic_weight,
    isotope_mass,
    ion_mass,
    particle_mass,
    is_stable,
    half_life,
    known_isotopes,
    common_isotopes,
    stable_isotopes,
    isotopic_abundance,
    integer_charge,
    electric_charge,
    periodic_table_period,
    periodic_table_block,
    periodic_table_category,
    periodic_table_group,
)

from ..nuclear import (
    nuclear_binding_energy,
    nuclear_reaction_energy,
)

from ...utils import (
    AtomicWarning,
    InvalidElementError,
    InvalidIsotopeError,
    InvalidIonError,
    ChargeError,
    AtomicError,
    MissingAtomicDataError,
    InvalidParticleError,
)

# (argument, expected)
atomic_symbol_table = [
    (1, 'H'),
    ('H', 'H'),
    ('p', 'H'),
    ('T', 'H'),
    ('deuterium', 'H'),
    ('deuteron', 'H'),
    ('Tritium', 'H'),
    ('triton', 'H'),
    ('H-2', 'H'),
    ('D', 'H'),
    ('T', 'H'),
    ('H-3', 'H'),
    ('Hydrogen-3', 'H'),
    ('helium', 'He'),
    (2, 'He'),
    ('alpha', 'He'),
    ('gold', 'Au'),
    ('Gold', 'Au'),
    (79, 'Au'),
    ('79', 'Au'),
    ('P', 'P'),
    (118, 'Og'),
    ('N-14', 'N'),
    ('N', 'N'),
    ('H +1', 'H'),
    ('H 1+', 'H'),
    ('hydrogen 1+', 'H'),
    ('deuterium 1+', 'H'),
    ('Fe 24+', 'Fe'),
    ('Fe +24', 'Fe'),
    ('Fe 2-', 'Fe'),
    ('Fe -2', 'Fe'),
    ('Fe+', 'Fe'),
    ('Fe++', 'Fe'),
    ('Fe-', 'Fe'),
    ('Fe++++++++++++++', 'Fe')]


@pytest.mark.parametrize(
    'argument, expected', atomic_symbol_table)
def test_atomic_symbol(argument, expected):
    """Test that `atomic_symbol` returns the expected result."""
    assert atomic_symbol(argument) == expected, \
        (f"atomic_symbol({repr(argument)}) is returning "
         f"{atomic_symbol(argument)} "
         f"which differs from the expected value of {repr(expected)}.")


# (argument, expected_error)
atomic_symbol_error_table = [
    ('H-0', InvalidParticleError),
    (3.14159, TypeError),
    ('Og-294b', InvalidParticleError),
    ('H-934361079326356530741942970523610389', InvalidParticleError),
    ('Fe 2+4', InvalidParticleError),
    ('Fe+24', InvalidParticleError),
    ('Fe +59', InvalidParticleError),
    ('C++++++++++++++++', InvalidParticleError),
    ('C-++++', InvalidParticleError),
    ('neutron', InvalidElementError),
    ('n', InvalidElementError),
    ('n-1', InvalidElementError),
    ('h', InvalidParticleError),
    ('d', InvalidParticleError),
    ('he', InvalidParticleError),
    ('au', InvalidParticleError),
    ('p-', InvalidElementError),
    (0, InvalidParticleError),
    (119, InvalidParticleError),
    ('antiproton', InvalidElementError)]


@pytest.mark.parametrize(
    'argument, expected_error', atomic_symbol_error_table)
def test_atomic_symbol_error(argument, expected_error):
    """Test that `atomic_symbol` raises the expected exceptions."""
    with pytest.raises(expected_error, message=(
            f"atomic_symbol({repr(argument)}) is not raising "
            f"{expected_error}.")):
        atomic_symbol(argument)


# (argument, expected)
isotope_symbol_table = [
    (('He', 4), 'He-4'),
    (('helium-4',), 'He-4'),
    (('H-2',), 'D'),
    (('Deuterium',), 'D'),
    (('deuterium',), 'D'),
    (('deuteron',), 'D'),
    (('tritium',), 'T'),
    (('triton',), 'T'),
    (('Hydrogen-3',), 'T'),
    (('hydrogen-3',), 'T'),
    (('H-3',), 'T'),
    ((1, 2), 'D'),
    (('Hydrogen', 3), 'T'),
    (('tritium',), 'T'),
    (('H', 2), 'D'),
    (('Alpha',), 'He-4'),
    (('alpha',), 'He-4'),
    ((79, 197), 'Au-197'),
    (('p',), 'H-1'),
    (('beryllium-8',), 'Be-8'),
    (('N-13',), 'N-13'),
    (('p',), 'H-1'),
    (('proton',), 'H-1'),
    (('protium',), 'H-1'),
    (('N-13 2+',), 'N-13'),
    (('Hydrogen-3 +1',), 'T'),
]


@pytest.mark.parametrize(
    "arguments, expected", isotope_symbol_table)
def test_isotope_symbol(arguments, expected):
    """Test that `isotope_symbol` returns the expected results."""
    assert isotope_symbol(*arguments) == expected, \
        (f"isotope_symbol is returning {isotope_symbol(*arguments)} "
         f"for arguments of {repr(arguments)}, which differs from the "
         f"expected value of {repr(expected)}.")


# (argument, kwargs, expected_error)
isotope_symbol_error_table = [
    ('Md-260', {"mass_numb": 261}, InvalidParticleError),
    ('protium', {"mass_numb": 2}, InvalidParticleError),
    ('alpha', {"mass_numb": 3}, InvalidParticleError),
    ('O-18', {"mass_numb": 19}, InvalidParticleError),
    ('lead-209', {"mass_numb": 511}, InvalidParticleError),
    ('He-1', {}, InvalidParticleError),
    (24, {"mass_numb": 23}, InvalidParticleError),
    ('H', {"mass_numb": 0}, InvalidParticleError),
    ('H-1', {"mass_numb": 2}, InvalidParticleError),
    ('P', {}, InvalidIsotopeError),
    (1, {}, InvalidIsotopeError),
    (4, {}, InvalidIsotopeError),
    ('hydrogen-444444', {}, InvalidParticleError),
    ('Fe', {"mass_numb": 2.1}, TypeError),
    ('He', {"mass_numb": 'c'}, TypeError),
    ('He-3', {"mass_numb": 4}, InvalidParticleError),
    ('D', {"mass_numb": 3}, InvalidParticleError),
    ('T', {"mass_numb": 2}, InvalidParticleError),
    ('Fe', {"mass_numb": None}, InvalidIsotopeError),
    ('He', {"mass_numb": 99}, InvalidParticleError),
    ('d', {}, InvalidParticleError),
    ('h-3', {}, InvalidParticleError),
    ('h', {}, InvalidParticleError),
    ('d+', {}, InvalidParticleError),
]


@pytest.mark.parametrize(
    "argument, kwargs, expected_error", isotope_symbol_error_table)
def test_isotope_symbol_error(argument, kwargs, expected_error):
    """Test that `isotope_symbol` raises the expected exceptions."""
    with pytest.raises(expected_error, message=(
            f"isotope_symbol({repr(argument)}, **{kwargs}) is not raising a "
            f"{expected_error}.")):
        isotope_symbol(argument, **kwargs)


# (argument, kwargs, expected_warning)
isotope_symbol_warning_table = [
    ('H-1', {"mass_numb": 1}, AtomicWarning),
    ('H-2', {"mass_numb": 2}, AtomicWarning),
    ('T', {"mass_numb": 3}, AtomicWarning),
    ('Li-6', {"mass_numb": 6}, AtomicWarning),
    ('lithium-6', {"mass_numb": 6}, AtomicWarning),
    ('alpha', {"mass_numb": 4}, AtomicWarning),
    ('p', {"mass_numb": 1}, AtomicWarning)]


@pytest.mark.parametrize(
    "argument, kwargs, expected_warning", isotope_symbol_warning_table)
def test_isotope_symbol_warnings(argument, kwargs, expected_warning):
    """Test that `isotope_symbol` issues the expected warnings."""
    with pytest.warns(expected_warning, message=(
            f"isotope_symbol({repr(argument)}, **{kwargs}) is not issuing a "
            f"{expected_warning}.")):
        isotope_symbol(argument, **kwargs)


# (argument, expected)
atomic_number_table = [
    ('H', 1),
    ('D', 1),
    ('deuterium', 1),
    ('Deuterium', 1),
    ('tritium', 1),
    ('p', 1),
    ('P', 15),
    ('Alpha', 2),
    ('C-12', 6),
    ('Argon', 18),
    ('protium', 1),
    ('H-3', 1),
    ('p+', 1),
    ('Be-8', 4),
    ('N', 7),
    ('N 2+', 7),
    ('N +1', 7),
    ('N+++', 7)]


@pytest.mark.parametrize("argument, expected", atomic_number_table)
def test_atomic_number(argument, expected):
    """Test that `atomic_number` returns the expected results."""
    assert atomic_number(argument) == expected, \
        (f"atomic_number({repr(argument)}) is expecting a result of "
         f"{repr(expected)} but "
         f"is getting a result of {atomic_number(argument)}.")


# (argument, expected_error)
atomic_number_error_table = [
    ('H-3934', InvalidParticleError),
    ('C-12b', InvalidParticleError),
    (-1.5, TypeError),
    ('n', InvalidElementError),
    ('n-1', InvalidElementError),
    ('neutron', InvalidElementError),
    ('Neutron', InvalidElementError),
    ('d', InvalidParticleError),
    ('t', InvalidParticleError),
    ('s-36', InvalidParticleError)]


@pytest.mark.parametrize(
    "argument, expected_error", atomic_number_error_table)
def test_atomic_number_error(argument, expected_error):
    """Test that `atomic_number` raises the expected exceptions."""
    with pytest.raises(expected_error, warning=(
            f"atomic_number({repr(argument)}) is not raising a "
            f"{expected_error}")):
        atomic_number(argument)


# (isotope, expected)
mass_number_table = [
    ('helium-3', 3),
    ('Au-197', 197),
    ('deuterium', 2),
    ('D', 2),
    ('H-2', 2),
    ('tritium', 3),
    ('T', 3),
    ('alpha', 4),
    ('p', 1),
    ('Be-8', 8),
    ('N-13', 13),
    ('N-13 2+', 13),
    ('N-13 +2', 13),
    ('N-13+++', 13)]


@pytest.mark.parametrize("isotope, expected", mass_number_table)
def test_mass_number(isotope, expected):
    """Test that `mass_number` returns the expected results."""
    assert mass_number(isotope) == expected, \
        (f"mass_number({repr(isotope)}) is returning a value of "
         f"{mass_number(isotope)}, which differs from the expected "
         f"value of {repr(expected)}.")


# (argument, expected_error)
mass_number_error_table = [
    ('H-359', InvalidParticleError),
    ('C-12b', InvalidParticleError),
    (-1.5, Exception),
    ('N-13+-+-', InvalidParticleError),
    ('h-3', InvalidParticleError),
    ('n', InvalidIsotopeError),
    ('n-1', InvalidIsotopeError),
]


@pytest.mark.parametrize(
    "argument, expected_error", mass_number_error_table)
def test_mass_number_error(argument, expected_error):
    """Test that `mass_number` raises the expected exceptions."""
    with pytest.raises(expected_error):
        mass_number(argument)


# (argument, expected)
element_name_table = [
    ('D', 'hydrogen'),
    ('deuterium', 'hydrogen'),
    ('Au', 'gold'),
    ('alpha', 'helium'),
    ('helium-4', 'helium'),
    ('H-2', 'hydrogen'),
    ('Deuterium', 'hydrogen'),
    ('Hydrogen-3', 'hydrogen'),
    ('hydrogen-3', 'hydrogen'),
    ('H-3', 'hydrogen'),
    ('tritium', 'hydrogen'),
    ('Alpha', 'helium'),
    ('alpha', 'helium'),
    (1, 'hydrogen'),
    (26, 'iron'),
    (79, 'gold'),
    ('p', 'hydrogen'),
    ('P', 'phosphorus'),
    ('Be-8', 'beryllium'),
    ('Li-7', 'lithium'),
    ('N', 'nitrogen'),
    ('N+++', 'nitrogen'),
    ('D-', 'hydrogen')]


@pytest.mark.parametrize("argument, expected", element_name_table)
def test_element_name(argument, expected):
    """Test that `element_name` returns the expected results."""
    assert element_name(argument) == expected, \
        (f"element_name({repr(argument)}) is returning a value of "
         f"{element_name(argument)}, which differs from the expected "
         f"value of {repr(expected)}.")


# (argument, expected_error)
element_name_error_table = [
    ('vegancupcakes', InvalidParticleError),
    ('C-+-', InvalidParticleError),
    (1.24, TypeError),
    ('n', InvalidElementError),
    ('neutron', InvalidElementError),
    (0, InvalidParticleError),
    ('H++', InvalidParticleError),
    ('t', InvalidParticleError),
    ('pb', InvalidParticleError),
    ('d', InvalidParticleError),
    ('h-3', InvalidParticleError),
    ('Pb-9', InvalidParticleError),
    ('H 2+', InvalidParticleError),
]


@pytest.mark.parametrize("argument, expected_error", element_name_error_table)
def test_element_name_error(argument, expected_error):
    """Test that `element_name` raises the expected exceptions."""
    with pytest.raises(expected_error):
        element_name(argument)


def test_standard_atomic_weight_value_between():
    """Test that `standard_atomic_weight` returns approximately the
    correct value for phosphorus."""
    assert 30.973 < standard_atomic_weight('P').to(u.u).value < 30.974, \
        "Incorrect standard atomic weight for phosphorus."


def test_standard_atomic_weight_unit():
    """Test that `standard_atomic_weight` returns a
    `~astropy.units.Quantity` with the expected units."""
    assert standard_atomic_weight('Au').unit == u.kg, \
        "Incorrect units from standard_atomic_weight for gold."


# (argument, expected)
standard_atomic_weight_table = [
    ('H', 1.008),
    (1, 1.008),
    ('Hydrogen', 1.008)]


@pytest.mark.parametrize("argument, expected", standard_atomic_weight_table)
def test_standard_atomic_weight(argument, expected):
    """Test that `standard_atomic_weight` returns the expected values
    for hydrogen."""
    assert (standard_atomic_weight(argument).to(u.u)).value == expected, \
        f"Incorrect standard_atomic_weight for {repr(argument)}."


# (argument, expected_error)
standard_atomic_weight_error_table = [
    ('H-1', AtomicError),
    ("help i'm trapped in a unit test", InvalidParticleError),
    (1.1, TypeError),
    ('n', InvalidElementError),
    ('p', AtomicError),
    ('alpha', AtomicError),
    ('deuteron', AtomicError),
    ('tritium', AtomicError),
    ('Au+', AtomicError),
    ('Fe -2', AtomicError),
    ('Og 2+', AtomicError),
    ('h', InvalidParticleError),
    ('fe', InvalidParticleError)]


@pytest.mark.parametrize("argument, expected_error",
                         standard_atomic_weight_error_table)
def test_standard_atomic_weight_error(argument, expected_error):
    """Test that `standard_atomic_weight` raises the expected
    exceptions."""
    with pytest.raises(expected_error, message=(
            f"standard_atomic_weight({repr(argument)}) is not raising a "
            "{expected_error}.")):
        standard_atomic_weight(argument)


def test_isotope_mass_berkelium_249():
    """Test that `isotope_mass` returns the correct value for Bk-249."""
    assert np.isclose(isotope_mass('berkelium-249').to(u.u).value, 249.0749877), \
        "Incorrect isotope mass for berkelium."


def test_isotope_mass_si_30_units():
    """Test that `isotope_mass` returns a `~astropy.units.Quantity` with
    the correct unit for Si-30."""
    assert isotope_mass('Si-30').unit == u.kg, \
        "Incorrect unit for isotope mass for Si-30."


# (arg1, arg2)
isotope_mass_table = [
    (('H-1',), ('protium',)),
    (('H-1',), (1, 1)),
    (('D',), ('H-2',)),
    (('H-2',), ('deuterium',)),
    (('deuterium',), (1, 2)),
    (('T',), ('H-3',)),
    (('H-3',), ('tritium',)),
    (('tritium',), (1, 3))]


@pytest.mark.parametrize("arg1, arg2", isotope_mass_table)
def test_isotope_mass(arg1, arg2):
    """Test that `isotope_mass` returns equivalent results for
    equivalent arguments."""
    assert isotope_mass(*arg1) == isotope_mass(*arg2), \
        f"isotope_mass(*{arg1}) is not equivalent to isotope_mass(*{arg2})"


# (argument, expected_error)
isotope_mass_error_table = [
    ("H", InvalidIsotopeError),
    (1.1, TypeError),
    ('alpha', AtomicError),
    ('He-4 2+', AtomicError),
    ('he-4', InvalidParticleError),
    ('Fe 2+', AtomicError),
    ('Fe -2', AtomicError),
    ('deuteron', AtomicError),
    ('triton', AtomicError),
    ('H-1 +1', AtomicError),
    ('H-1+', AtomicError)]


@pytest.mark.parametrize("argument, expected_error", isotope_mass_error_table)
def test_isotope_mass_error(argument, expected_error):
    """Test that `isotope_mass` raises the expected exceptions."""
    with pytest.raises(expected_error, warning=(
            f"isotope_mass({repr(argument)}) is not raising a "
            f"{expected_error}")):
        isotope_mass(argument)


def test_ion_mass_for_hydrogen_with_no_mass_number():
    """Test that `ion_mass` does not return the proton mass when no
    mass number is specified for hydrogen.  In this case, the
    standard atomic weight should be used to account for the small
    fraction of deuterium."""
    assert ion_mass('H', Z=1) > const.m_p
    assert ion_mass('hydrogen', Z=1) > const.m_p


def test_ion_mass_unit():
    """Test that `ion_mass` returns a `~astropy.units.Quantity` with the
    correct units."""
    assert ion_mass('F-19', Z=3).unit == u.kg


# (arg, kwargs)
inputs_that_should_return_proton_mass = [
    ('proton', {}),
    ('H-1+', {}),
    ('H-1 +1', {}),
    ('H-1 1+', {}),
    ('H-1', {'Z': 1}),
    ('hydrogen-1', {'Z': 1}),
    ('p+', {}),
]


@pytest.mark.parametrize("arg, kwargs", inputs_that_should_return_proton_mass)
def test_ion_mass_proton_mass(arg, kwargs):
    """Test that `ion_mass` returns the proton mass
    `~astropy.constants.Constant` for appropriate inputs."""
    should_be_proton_mass = ion_mass(arg, **kwargs)
    assert should_be_proton_mass == const.m_p, \
        (f"ion_mass({repr(arg)}, **{kwargs}) should be returning the proton "
         f"mass, but is instead returning {repr(should_be_proton_mass)}.")


def test_ion_mass_miscellaneous_cases():
    """Test miscellaneous cases for `ion_mass`."""
    assert ion_mass('alpha') > ion_mass('He-3 2+')


# (arg1, kwargs1, arg2, kwargs2, expected)
equivalent_ion_mass_args = [
    ('e+', {}, 'positron', {}, const.m_e),
    ('alpha', {}, 'He-4++', {}, None),
    ('alpha', {}, 'helium-4 2+', {}, None),
    ('deuteron', {}, 'H', {'Z': 1, 'mass_numb': 2}, None),
    ('D+', {}, 'H-2+', {}, None),
    ('D+', {}, 'D 1+', {}, None),
    ('Deuterium+', {}, 'D', {'Z': 1}, None),
    ('triton', {}, 'H', {'Z': 1, 'mass_numb': 3}, None),
    ('T+', {}, 'H-3+', {}, None),
    ('T+', {}, 'T 1+', {}, None),
    ('Tritium+', {}, 'T', {'Z': 1}, None),
    ('Fe-56 1+', {}, 'Fe', {'mass_numb': 56, 'Z': 1},
     ion_mass('Fe-56 1-') - 2 * const.m_e),
    ('Fe-56 +1', {}, 26, {'mass_numb': 56, 'Z': 1}, None),
]


@pytest.mark.parametrize(
    "arg1, kwargs1, arg2, kwargs2, expected", equivalent_ion_mass_args)
def test_ion_mass_equivalent_args(arg1, kwargs1, arg2, kwargs2, expected):
    """Test that `ion_mass` returns equivalent results for equivalent
    positional and keyword arguments."""

    result1 = ion_mass(arg1, **kwargs1)
    result2 = ion_mass(arg2, **kwargs2)

    assert result1 == result2, \
        (f"ion_mass({repr(arg1)}, **{kwargs1}) = {repr(result1)}, whereas "
         f"ion_mass({repr(arg2)}, **{kwargs2}) = {repr(result2)}.  "
         f"These results are not equivalent as expected.")

    if expected is not None:
        assert result1 == result2 == expected, \
            (f"ion_mass({repr(arg1)}, **{kwargs1}) = {repr(result1)} and "
             f"ion_mass({repr(arg2)}, **{kwargs2}) = {repr(result2)}, but  "
             f"these results are not equal to {repr(expected)} as expected.")


# (argument, kwargs, expected_error)
ion_mass_error_table = [
    ('Og 1+', {}, MissingAtomicDataError),
    ('Fe-56', {"Z": 1.4}, TypeError),
    ('n', {}, InvalidIonError),
    ('H-1 +1', {"Z": 0}, AtomicError),
    (26, {"Z": 1, "mass_numb": 'a'}, TypeError),
    (26, {"Z": 27, "mass_numb": 56}, InvalidParticleError),
    ('Og', {"Z": 1}, MissingAtomicDataError),
    ('Og', {"mass_numb": 696, "Z": 1}, InvalidParticleError),
    ('He 1+', {"mass_numb": 99}, InvalidParticleError),
    ('fe-56 1+', {}, InvalidParticleError)]


@pytest.mark.parametrize("argument, kwargs, expected_error",
                         ion_mass_error_table)
def test_ion_mass_error(argument, kwargs, expected_error):
    """Test exceptions that should be raised by `ion_mass`."""
    with pytest.raises(expected_error, message=(
            f"ion_mass({repr(argument)}, **{kwargs}) is not raising a "
            f"{repr(expected_error)}.")):
        ion_mass(argument, **kwargs)


# (argument, kwargs, expected_warning)
ion_mass_warning_table = [
    ('H-1', {'mass_numb': 1, 'Z': 1}, AtomicWarning),
]


@pytest.mark.parametrize("argument, kwargs, expected_warning",
                         ion_mass_warning_table)
def test_ion_mass_warnings(argument, kwargs, expected_warning):
    """Test that `ion_mass` issues the expected warnings."""
    with pytest.warns(expected_warning, message=(
            f"ion_mass({repr(argument)}, **{kwargs}) is not issuing a "
            f"{expected_warning}.")):
        ion_mass(argument, **kwargs)


# (argument)
is_stable_table = [
    ('H-1',),
    (1, 1),
    ('N-14',),
    ('N', 14),
    ('P-31',),
    ('P', 31),
    ('p',),
    ('alpha',),
    ('Xe-124',),
    ('Fe', 56),
    ('Fe-56',),
    ('iron-56',),
    ('Iron-56',),
    (26, 56),
]


@pytest.mark.parametrize("argument", is_stable_table)
def test_is_stable(argument):
    """Test that `is_stable` returns `True` for stable isotopes."""
    assert is_stable(*argument), \
        f"is_stable is not returning True for {repr(argument)}"


# (argument)
is_stable_false_table = [
    ('Be-8',),
    ('U-235',),
    ('uranium-235',),
    ('T',),
    (4, 8),
    ('tritium',),
    ('Pb-209',),
    ('lead-209',),
    ('Lead-209',),
    ('Pb', 209),
    (82, 209),
]


@pytest.mark.parametrize("argument", is_stable_false_table)
def test_is_stable_false(argument):
    """Test that `is_stable` returns `False` for unstable isotopes."""
    assert not is_stable(*argument), \
        f"is_stable is not returning False for {repr(argument)}"


# (argument, expected_error)
is_stable_error_table = [
    (('hydrogen-444444',), InvalidParticleError),
    (('hydrogen', 0), InvalidParticleError),
    (('',), InvalidParticleError),
    (('pb-209',), InvalidParticleError),
    (('h',), InvalidParticleError)]


@pytest.mark.parametrize("argument, expected_error",
                         is_stable_error_table)
def test_is_stable_error(argument, expected_error):
    """Test exceptions that should be raised by `is_stable`."""
    with pytest.raises(expected_error, message=(
            f"is_stable({repr(argument)}) is not raising a "
            f"{expected_error}")):
        is_stable(*argument)


def test_known_common_stable_isotopes():
    """Test that `known_isotopes`, `common_isotopes`, and
    `stable_isotopes` return the correct values for hydrogen."""

    known_should_be = ['H-1', 'D', 'T', 'H-4', 'H-5', 'H-6', 'H-7']
    common_should_be = ['H-1', 'D']
    stable_should_be = ['He-3', 'He-4']

    assert known_isotopes('H') == known_should_be, \
        (f"known_isotopes('H') should return {known_should_be}, but is "
         f"instead returning {known_isotopes('H')}")

    assert common_isotopes('H') == common_should_be, \
        (f"common_isotopes('H') should return {common_should_be}, but is "
         f"instead returning {common_isotopes('H')}")

    assert stable_isotopes('He') == stable_should_be, \
        (f"stable_isotopes('He') should return {stable_should_be}, but is "
         f"instead returning {stable_isotopes('He')}")


def test_half_life():
    """Test that `half_life` returns the correct values for various
    isotopes."""
    assert half_life('H-1') == np.inf * u.s, "Incorrect half-life for H-1'."
    assert np.isclose(half_life('tritium').to(u.s).value,
                      (12.32 * u.yr).to(u.s).value, rtol=2e-4), \
        "Incorrect half-life for tritium."
    assert half_life('H-1').unit == 's', "Incorrect unit for H-1."
    assert half_life('tritium').unit == 's', "Incorrect unit for tritium."


def test_half_life_unstable_isotopes():
    """Test that `half_life` returns `None` and raises an exception for
    all isotopes that do not yet have half-life data."""
    for isotope in _Isotopes.keys():
        if 'half_life' not in _Isotopes[isotope].keys() and \
                not _Isotopes[isotope].keys():
            with pytest.raises(MissingAtomicDataError):
                half_life(isotope)


def test_half_life_u_220():
    """Test that `half_life` returns `None` and issues a warning for an
    isotope without half-life data."""

    isotope_without_half_life_data = "No-248"

    with pytest.raises(MissingAtomicDataError, message=(
            f"This test assumes that {isotope_without_half_life_data} does "
            f"not have half-life data.  If half-life data is added for this "
            f"isotope, then a different isotope that does not have half-life "
            f"data should be chosen for this test.")):

        half_life(isotope_without_half_life_data)


atomic_TypeError_funcs_table = [
    atomic_symbol,
    isotope_symbol,
    atomic_number,
    is_stable,
    half_life,
    mass_number,
    element_name,
    standard_atomic_weight,
    isotope_mass,
    ion_mass,
    nuclear_binding_energy,
    nuclear_reaction_energy
]

atomic_TypeError_bad_arguments = [1.1, {'cats': 'bats'}, 1 + 1j]


@pytest.mark.parametrize(
    "func, argument",
    product(atomic_TypeError_funcs_table,
            atomic_TypeError_bad_arguments))
def test_atomic_TypeErrors(func, argument):
    """Test that atomic functions raise a `TypeError` when arguments of
    the incorrect type are provided."""
    with pytest.raises(TypeError):
        func(argument)


atomic_ParticleErrors_funcs_table = [
    atomic_symbol,
    isotope_symbol,
    atomic_number,
    is_stable,
    half_life,
    mass_number,
    element_name,
    standard_atomic_weight,
    isotope_mass,
    ion_mass,
    particle_mass,
    known_isotopes,
    stable_isotopes,
    common_isotopes,
    isotopic_abundance,
    integer_charge,
    electric_charge,
]

atomic_ParticleError_bad_arguments = [
    -1,
    119,
    'grumblemuffins',
    'H-0',
    'Og-294b',
    'H-9343610',
    'Fe 2+4',
    'Fe+24',
    'Fe +59',
    'C++++++++++++++++',
    'C-++++',
    'h',
    'd',
    'he',
    'au',
    'alpha 1+',
    'alpha-4',
]


@pytest.mark.parametrize(
    "func, argument",
    product(atomic_ParticleErrors_funcs_table,
            atomic_ParticleError_bad_arguments))
def test_atomic_ParticleErrors(func, argument):
    """Test that atomic functions raise an
    `~plasmapy.utils.InvalidParticleErrors` when incorrect arguments are
    provided."""
    with pytest.raises(InvalidParticleError):
        func(argument)


def test_known_common_stable_isotopes_cases():
    """Test that known_isotopes, common_isotopes, and stable_isotopes
    return certain isotopes that fall into these categories."""
    assert 'H-1' in known_isotopes('H')
    assert 'D' in known_isotopes('H')
    assert 'T' in known_isotopes('H')
    assert 'Be-8' in known_isotopes('Be')
    assert 'Og-294' in known_isotopes(118)
    assert 'H-1' in common_isotopes('H')
    assert 'H-4' not in common_isotopes(1)
    assert 'H-1' in stable_isotopes('H')
    assert 'D' in stable_isotopes('H')
    assert 'T' not in stable_isotopes('H')
    assert 'Fe-56' in common_isotopes('Fe', most_common_only=True)
    assert 'He-4' in common_isotopes('He', most_common_only=True)


def test_known_common_stable_isotopes_len():
    """Test that `known_isotopes`, `common_isotopes`, and
    `stable_isotopes` each return a `list` of the expected length.

    The number of common isotopes may change if isotopic composition
    data has any significant changes.

    The number of stable isotopes may decrease slightly if some isotopes
    are discovered to be unstable but with extremely long half-lives.

    The number of known isotopes will increase as new isotopes are
    discovered, so a buffer is included in the test."""

    assert len(common_isotopes()) == 288, \
        ("The length of the list returned by common_isotopes() is "
         f"{len(common_isotopes())}, which is not the expected value.")

    assert len(stable_isotopes()) == 254, \
        ("The length of the list returned by stable_isotopes() is "
         f"{len(stable_isotopes())}, which is not the expected value.")

    assert 3352 <= len(known_isotopes()) <= 3400, \
        ("The length of the list returned by known_isotopes() is "
         f"{len(known_isotopes())}, which is not within the expected range.")


@pytest.mark.parametrize(
    "func", [common_isotopes, stable_isotopes, known_isotopes])
def test_known_common_stable_isotopes_error(func):
    """Test that `known_isotopes`, `common_isotopes`, and
    `stable_isotopes` raise an `~plasmapy.utils.InvalidElementError` for
    neutrons."""
    with pytest.raises(InvalidElementError, message=(
            f"{func} is not raising a ElementError for neutrons.")):
        func('n')


def test_isotopic_abundance():
    """Test that `isotopic_abundance` returns the appropriate values or
    raises appropriate errors for various isotopes."""
    assert isotopic_abundance('H', 1) == isotopic_abundance('protium')
    assert np.isclose(isotopic_abundance('D'), 0.000115)
    assert isotopic_abundance('Be-8') == 0.0, 'Be-8'
    assert isotopic_abundance('Li-8') == 0.0, 'Li-8'

    with pytest.warns(AtomicWarning):
        isotopic_abundance('Og', 294)

    with pytest.raises(InvalidIsotopeError, message="No exception raised for "
                                                    "neutrons"):
        isotopic_abundance('neutron')

    with pytest.raises(InvalidParticleError):
        isotopic_abundance('Og-2')


isotopic_abundance_elements = (
    atomic_number(atomic_numb) for atomic_numb in range(1, 119))

isotopic_abundance_isotopes = (
    common_isotopes(element) for element in isotopic_abundance_elements)

isotopic_abundance_sum_table = (
    (element, isotopes) for element, isotopes in
    zip(isotopic_abundance_elements, isotopic_abundance_isotopes)
    if isotopes)


@pytest.mark.parametrize("element, isotopes", isotopic_abundance_sum_table)
def test_isotopic_abundances_sum(element, isotopes):
    """Test that the sum of isotopic abundances for each element with
    isotopic abundances is one."""
    sum_of_iso_abund = sum(isotopic_abundance(isotope) for isotope in isotopes)
    assert np.isclose(sum_of_iso_abund, 1, atol=1e-6), \
        f"The sum of the isotopic abundances for {element} does not equal 1."


# (argument, expected)
integer_charge_table = [
    ('H+', 1),
    ('D +1', 1),
    ('tritium 1+', 1),
    ('H-', -1),
    ('Fe -2', -2),
    ('Fe 2-', -2),
    ('N--', -2),
    ('N++', 2),
    ('alpha', 2),
    ('proton', 1),
    ('deuteron', 1),
    ('triton', 1),
    ('electron', -1),
    ('e-', -1),
    ('e+', 1),
    ('positron', 1),
    ('n', 0),
    ('neutron', 0),
    ('p-', -1),
    ('antiproton', -1),
]


@pytest.mark.parametrize("argument, expected", integer_charge_table)
def test_integer_charge(argument, expected):
    """Test that `integer_charge` returns the expected results."""
    assert integer_charge(argument) == expected, \
        (f"integer_charge({repr(argument)}) is returning "
         f"{integer_charge(argument)} which differs from the expected result "
         f"of {expected}.")


# (argument, expected_error)
integer_charge_error_table = [
    ('fads', InvalidParticleError),
    ('H++', InvalidParticleError),
    ('h+', InvalidParticleError),
    ('fe 1+', InvalidParticleError),
    ('d+', InvalidParticleError),
    ('Fe 29+', InvalidParticleError),
    ('H-1', ChargeError),
]


@pytest.mark.parametrize("argument, expected_error",
                         integer_charge_error_table)
def test_integer_charge_error(argument, expected_error):
    """Test that `integer_charge` raises the expected exceptions."""
    with pytest.raises(expected_error, message=(
            f"integer_charge({repr(argument)} is not raising a "
            f"{expected_error}.")):
        integer_charge(argument)


# (argument, expected_warning)
integer_charge_warning_table = [
    ('H---', AtomicWarning),
    ('Fe -26', AtomicWarning),
    ('Og 10-', AtomicWarning)]


@pytest.mark.parametrize("argument, expected_warning",
                         integer_charge_warning_table)
def test_integer_charge_warnings(argument, expected_warning):
    """Test that `integer_charge` issues appropriate warnings."""
    with pytest.warns(expected_warning, message=(
            f"integer_charge({repr(argument)}) is not issuing "
            f"{expected_warning}")):
        integer_charge(argument)


def test_electric_charge():
    """Test that the results from `electric_charge` provide the correct
    values that have the correct characteristics."""
    assert electric_charge('p').value == 1.6021766208e-19
    assert electric_charge('p').unit == 'C'
    assert electric_charge('e').value == -1.6021766208e-19
    assert electric_charge('alpha').value == 3.2043532416e-19
    assert electric_charge('n').value == 0


# (argument, expected_error)
electric_charge_error_table = [
    ('badinput', InvalidParticleError),
    ('h+', InvalidParticleError),
    ('Au 81+', InvalidParticleError)]


@pytest.mark.parametrize("argument, expected_error",
                         electric_charge_error_table)
def test_electric_charge_error(argument, expected_error):
    """Test that `electric_charge` raises the expected exceptions."""
    with pytest.raises(expected_error, message=(
            f"electric_charge({repr(argument)}) is not raising a "
            f"{expected_error}.")):
        electric_charge(argument)


# (argument, expected_warning)
electric_charge_warning_table = [
    ('Au 81-', AtomicWarning),
    ('H---', AtomicWarning)]


@pytest.mark.parametrize("argument, expected_warning",
                         electric_charge_warning_table)
def test_electric_charge_warning(argument, expected_warning):
    """Test that `electric_charge` issues the expected warnings."""
    with pytest.warns(expected_warning, message=(
            f"electric_charge({repr(argument)}) is not issuing a "
            f"{expected_warning}.")):
        electric_charge(argument)


def test_particle_mass():
    r"""Quick tests to make sure that `particle_mass` gives consistent
    results with other mass functions."""
    assert ion_mass('p+') == particle_mass('p+')
    assert standard_atomic_weight('H') == particle_mass('H')
    assert isotope_mass('D') == particle_mass('D')
