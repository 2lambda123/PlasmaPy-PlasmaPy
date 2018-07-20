from typing import Dict, List, Optional, Tuple, Union

import astropy.units as u
import collections
import numpy as np
import numbers
from plasmapy.atomic.atomic import atomic_number
from plasmapy.atomic.particle_class import Particle
from plasmapy.atomic.particle_input import particle_input
from plasmapy.atomic.symbols import particle_symbol
from plasmapy.utils import (AtomicError, ChargeError, InvalidParticleError, check_quantity)

State = collections.namedtuple(
    'State', [
        'integer_charge',
        'ionic_fraction',
        'ionic_symbol',
    ])

_number_density_errmsg = (
    "Number densities must be Quantity objects with units of inverse "
    "volume."
)


class IonizationState:
    """
    Representation of the ionization state distribution of a single
    element or isotope.

    Parameters
    ----------
    particle: str, integer, or ~plasmapy.atomic.Particle
        A `str` or `~plasmapy.atomic.Particle` instance representing
        an element or isotope, or an integer representing the atomic
        number of an element.

    ionic_fractions: ~numpy.ndarray, list, tuple, or ~astropy.units.Quantity
        The ionization fractions of an element, where the indices
        correspond to integer charge.  This argument should contain the
        atomic number plus one items, and must sum to one within an
        absolute tolerance of `tol` if dimensionless.  Alternatively,
        this argument may be a `~astropy.units.Quantity` that represents
        the number densities of each neutral/ion.

    T_e: ~astropy.units.Quantity, keyword-only, optional
        The electron temperature or thermal energy per particle.

    n_e: ~astropy.units.Quantity, keyword-only, optional
        The electron number density.

    n_elem: ~astropy.units.Quantity, keyword-only, optional
        The number density of the element, including neutrals and all
        ions.

    tol: float or int, keyword-only, optional
        The absolute tolerance used by `~numpy.isclose` when testing
        normalizations and making comparisons.  Defaults to `1e-15`.

    Raises
    ------
    ~plasmapy.utils.AtomicError
        If the ionic fractions are not normalized or contain invalid
        values

    ~plasmapy.utils.InvalidParticleError
        If the particle is invalid.

    Examples
    --------
    >>> states = IonizationState('H', [0.6, 0.4], n_elem=1*u.cm**-3, T_e=11000*u.K)
    >>> states.ionic_fractions
    array([0.6, 0.4])
    >>> states.n_e  # electron number density
    <Quantity 400000. 1 / m3>
    >>> states.n_elem  # element number density
    <Quantity 1000000. 1 / m3>

    Notes
    -----
    Only one of `n_e` and `n_elem` may be set.

    """

    # TODO: Allow this class to (optionally?) handle negatively charged
    # ions.  There are instances where singly negatively charged ions
    # are important in astrophysical plasmas, such as H- in the
    # atmospheres of relatively cool stars.  There may be some rare
    # situations where doubly negatively charged ions show up too,
    # though triply negatively charged ions are very unlikely.

    # TODO: Add in functionality to find equilibrium ionization states.
    # How much data will this require?

    @check_quantity(
        T_e={"units": u.K, "none_shall_pass": True},
        n_e={"units": u.m ** -3, "none_shall_pass": True},
        n_elem={"units": u.m ** -3, "none_shall_pass": True},
    )
    @particle_input(require='element', exclude='ion')
    def __init__(self,
                 particle: Particle,
                 ionic_fractions=None,
                 *,
                 T_e=None,
                 n_e=None,
                 n_elem=None,
                 tol: Union[float, int] = 1e-15):
        """Initialize a `~plasmapy.atomic.IonizationState` instance."""

        self._particle = particle

        try:
            self.tol = tol
            self.T_e = T_e
            self.n_elem = n_elem
            self.n_e = n_e
            self.ionic_fractions = ionic_fractions

            # if self._ionic_fractions is None and self.T_e is not None:
            #     self.equilibrate()

        except Exception as exc:
            raise AtomicError(
                f"Unable to create IonizationState instance for "
                f"{particle.particle}.") from exc

    def __getitem__(self, value) -> State:
        """Return the ionic fraction(s)."""
        if isinstance(value, slice):
            raise TypeError("IonizationState instances cannot be sliced.")

        if isinstance(value, numbers.Integral) and 0 <= value <= self.atomic_number:
            result = State(value, self.ionic_fractions[value], self.ionic_symbols[value])
        else:
            if not isinstance(value, Particle):
                try:
                    value = Particle(value)
                except InvalidParticleError as exc:
                    raise InvalidParticleError(
                        f"{value} is not a valid integer charge or "
                        f"particle.") from exc

            same_element = value.element == self.element
            same_isotope = value.isotope == self.isotope
            has_charge_info = value.is_category(any_of=["charged", "uncharged"])

            if same_element and same_isotope and has_charge_info:
                Z = value.integer_charge
                result = State(Z, self.ionic_fractions[Z], self.ionic_symbols[Z])
            else:
                if not same_element or not same_isotope:
                    raise AtomicError("Inconsistent element or isotope.")
                elif not has_charge_info:
                    raise ChargeError("No integer charge provided.")
        return result

    def __iter__(self):
        """Initialize the instance prior to an iteration."""
        self._charge_index = 0
        return self

    def __next__(self):
        """
        Return a `~State` `~collections.namedtuple` which contains
        ``integer_charge``, ``ionic_fraction``, and ``ionic_symbol``.
        """
        if self._charge_index <= self.atomic_number:
            result = State(
                self._charge_index,
                self._ionic_fractions[self._charge_index],
                self.ionic_symbols[self._charge_index],
            )
            self._charge_index += 1
            return result
        else:
            del self._charge_index
            raise StopIteration

    def __eq__(self, other):
        """
        Return `True` if the ionic fractions for two `IonizationState`
        instances are approximately equal to within the minimum `tol`
        specified by either, and `False` otherwise.

        Raises
        ------
        AtomicError
            If `other` is not an `~plasmapy.atomic.IonizationState`
            instance, or if `other` corresponds to a different element.

        Examples
        --------
        >>> IonizationState('H', [1, 0], tol=1e-6) == IonizationState('H', [1, 1e-6], tol=1e-6)
        True
        >>> IonizationState('H', [1, 0], tol=1e-8) == IonizationState('H', [1, 1e-6], tol=1e-5)
        False

        """
        if not isinstance(other, IonizationState):
            raise AtomicError(
                "Instances of the IonizationState class may only be "
                "compared with other IonizationState instances.")

        if self.element != other.element:
            raise AtomicError("Only ionization states of the same element may be compared.")

        # Use the tightest of the two absolute tolerances
        min_tol = np.min([self.tol, other.tol])

        return np.allclose(self.ionic_fractions, other.ionic_fractions, atol=min_tol)

    @property
    def ionic_fractions(self) -> np.ndarray:
        """
        Return the ionic fractions, where the index corresponds to
        the integer charge.

        Examples
        --------
        >>> hydrogen_states = IonizationState('H', [0.9, 0.1])
        >>> hydrogen_states.ionic_fractions
        array([0.9, 0.1])

        """
        return self._ionic_fractions

    @ionic_fractions.setter
    def ionic_fractions(self, fractions):
        """
        Set the ionic fractions, while checking that the new values are
        valid and normalized to one.
        """

        if fractions is None:
            self._ionic_fractions = np.full(self.atomic_number + 1, np.nan, dtype=np.float64)
        else:
            try:
                if not isinstance(fractions, np.ndarray) or 'float' not in str(fractions.dtype):
                    fractions = np.array(fractions, dtype=np.float)
            except Exception as exc:
                raise AtomicError(
                    f"Unable to set ionic fractions of {self.element} "
                    f"to {fractions}.") from exc

            if np.min(fractions) < 0:
                raise AtomicError("Ionic fractions cannot be negative.")

            if isinstance(fractions, u.Quantity):
                if self._n_e is not None or self._n_elem is not None:
                    raise AtomicError(
                        "The ionization state may be set using number "
                        "densities for each ion only if neither of the "
                        "electron density and element density has "
                        "already been set.")
                self.number_densities = fractions
            else:

                if not np.any(np.isnan(fractions)):

                    total = np.sum(fractions)
                    if not np.isclose(total, 1, atol=self.tol, rtol=0):
                        raise AtomicError(
                            f"The sum of the ionic fractions of {self.element} "
                            f"equals {total}, which is not approximately one.")
                    if not len(fractions) == self.atomic_number + 1:
                        raise AtomicError(
                            f"len(fractions) equals {len(fractions)}, but "
                            f"should equal {self.atomic_number + 1} which "
                            f"is the atomic number of {self.element} + 1."
                        )

                self._ionic_fractions = fractions

    @property
    def n_e(self):
        """
        Return the electron number density assuming a single species
        plasma.
        """
        if self._n_e is not None:
            return self._n_e
        elif self._n_elem is not None:
            return np.sum(self._n_elem * self.ionic_fractions * self.integer_charges)
        else:
            raise AtomicError(
                "Insufficient information to calculate the electron "
                "density.")

    @n_e.setter
    def n_e(self, value):
        """
        Return the electron density assuming a single-species
        plasma.
        """
        if value is None:
            self._n_e = None
            return
        elif self._n_elem is not None:
            raise AtomicError(
                "Only one of n_e and n_elem may be set for a "
                "single element, quasineutral plasma.")
        try:
            self._n_e = value.to(u.m ** -3)
            self._n_elem = None
        except (AttributeError, u.UnitConversionError):
            raise AtomicError(_number_density_errmsg)

    @property
    def n_elem(self):
        """
        Return the number density of atoms plus ions for this
        species.
        """
        if self._n_elem is not None:
            return self._n_elem
        elif self._n_e is not None:
            return self._n_e / (self.ionic_fractions * self.integer_charges)

    @n_elem.setter
    def n_elem(self, value):
        """The number density of atoms plus ions of this species."""
        if value is None:
            self._n_elem = None
        else:
            if '_n_e' in dir(self) and self._n_e is not None:
                raise AtomicError(
                    "Only one of n_e and n_elem may be set for a "
                    "single element, quasineutral plasma.")
            try:
                self._n_elem = value.to(u.m ** -3)
            except (AttributeError, u.UnitConversionError):
                raise AtomicError(_number_density_errmsg) from None

    @property
    def number_densities(self):
        """Return the number densities for each state."""
        if self._n_e is not None or self._n_elem is not None:
            return (self.n_elem * self.ionic_fractions).to(u.m ** -3)
        else:
            raise AtomicError(
                "Insufficient information to return number densities.")

    @number_densities.setter
    def number_densities(self, value: u.m ** -3):
        if self._n_elem is not None or self._n_e is not None:
            raise AtomicError
        if not isinstance(value, u.Quantity):
            raise TypeError
        if np.any(value < 0):
            raise AtomicError("Number densities cannot be negative.")
        try:
            value = value.to(u.m ** -3)
        except (AttributeError, u.UnitsError):
            raise AtomicError

        self._n_elem = value.sum()
        self._ionic_fractions = value / self._n_elem

    @property
    def T_e(self):
        """Return the electron temperature."""
        if self._T_e is None:
            raise AtomicError("No electron temperature has been specified.")
        return self._T_e.to(u.K, equivalencies=u.temperature_energy())

    @T_e.setter
    def T_e(self, value):

        if value is None:
            self._T_e = None
        else:
            try:
                value = value.to(u.K, equivalencies=u.temperature_energy())
            except (AttributeError, u.UnitsError):
                raise AtomicError("Invalid temperature.") from None
            self._T_e = value

    @property
    def equil_ionic_fractions(self, T_e=None):
        """
        Return the equilibrium ionic fractions for temperature `T_e` or
        the temperature set in the IonizationState instance.  Not
        implemented.
        """
        raise NotImplementedError

    def equilibrate(self, T_e=None):
        """
        Set the ionic fractions to collisional ionization equilibrium
        for temperature `T_e`.  Not implemented.
        """
        # self.ionic_fractions = self.equil_ionic_fractions
        raise NotImplementedError

    @property
    def atomic_number(self) -> int:
        """Return the atomic number of the element."""
        return self._particle.atomic_number

    @property
    def element(self) -> str:
        """Return the atomic symbol of the element."""
        return self._particle.element

    @property
    def isotope(self) -> str:
        """
        Return the isotope symbol for an isotope, or `None` if the
        particle is not an isotope.
        """
        return self._particle.isotope

    @property
    def atom(self) -> str:
        """
        Return the element or isotope corresponding to this
        `~plasmapy.atomic.IonizationState` instance.
        """
        return self._particle.particle

    @property
    def particles(self) -> List[Particle]:
        """
        Return a list of the `~plasmapy.atomic.Particle` class
        instances.
        """
        return [Particle(self._particle.particle, Z=i) for i in range(self.atomic_number + 1)]

    @property
    def ionic_symbols(self) -> List[str]:
        """Return the ionic symbols for all charge states."""
        return [p.ionic_symbol for p in self.particles]

    @property
    def integer_charges(self) -> np.ndarray:
        """Return an array with the integer charges."""
        return np.arange(0, self.atomic_number + 1, dtype=np.int)

    @property
    def Z_mean(self) -> np.float64:
        """Return the mean integer charge"""
        if np.nan in self.ionic_fractions:
            raise ChargeError(
                "Z_mean cannot be found because no ionic fraction "
                f"information is available for {self.particle}.")
        return np.sum(self.ionic_fractions * np.arange(self.atomic_number + 1))

    @property
    def Z_rms(self) -> np.float64:
        """Return the root mean square integer charge."""
        return np.sqrt(np.sum(self.ionic_fractions * np.arange(self.atomic_number + 1) ** 2))

    def is_normalized(self, tol: numbers.Integral = None) -> bool:
        """
        Return `True` if the sum of the ionization fractions is equal to
        one within the allowed tolerance, and `False` otherwise.
        """
        tol = tol if tol is not None else self.tol
        if not isinstance(tol, numbers.Real):
            raise TypeError("tol must be an int or float.")
        if not 0 <= tol < 1:
            raise ValueError("Need 0 <= tol < 1.")
        total = np.sum(self._ionic_fractions)
        return np.isclose(total, 1, atol=tol, rtol=0)

    def normalize(self):
        """
        Normalize the ionization state distribution so that the sum
        becomes equal to one.
        """
        self._ionic_fractions = self._ionic_fractions / np.sum(self._ionic_fractions)

    @property
    def tol(self) -> numbers.Real:
        """Return the absolute tolerance for comparisons."""
        return self._tol

    @tol.setter
    def tol(self, atol: numbers.Real):
        """Set the absolute tolerance for comparisons."""
        if not isinstance(atol, numbers.Real):
            raise TypeError("The attribute tol must be a real number.")
        if 0 <= atol < 1:
            self._tol = atol
        else:
            raise ValueError("Need 0 <= tol < 1.")
