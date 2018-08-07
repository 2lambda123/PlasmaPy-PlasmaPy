"""Classes for storing ionization state data."""

from typing import Dict, List, Optional, Tuple, Union
import astropy.units as u
import collections
import numpy as np
import numbers
from plasmapy.atomic.atomic import atomic_number
from plasmapy.atomic.particle_class import Particle
from plasmapy.atomic.symbols import particle_symbol
from plasmapy.utils import (AtomicError, ChargeError, InvalidParticleError, check_quantity)
from plasmapy.atomic.ionization_state import (State, IonizationState, _number_density_errmsg)


class IonizationStates:
    """
    Describe the ionization state distributions of multiple elements.

    Parameters
    ----------
    inputs: `list`, `tuple`, or `dict`
        A `list` or `tuple` of elements or isotopes (if `T_e` is
        provided); a `list` of `~plasmapy.atomic.IonizationState`
        instances; a `dict` with elements or isotopes as keys and
        a `~numpy.ndarray` of ionic fractions as the values; or a `dict`
        with elements or isotopes as keys and `~astropy.units.Quantity`
        instances with units of number density.

    T_e: `~astropy.units.Quantity`, optional, keyword-only
        The electron temperature in units of temperature or thermal
        energy per particle.

    equilibrate: `bool`, optional, keyword-only
        Set the ionic fractions to the estimated collisional ionization
        equilibrium.  Not implemented.

    abundances: `dict` or `str`, optional, keyword-only
        The relative abundances of each element in the plasma.

    log_abundances: `dict`, optional, optional, keyword-only
        The base 10 logarithm of the relative abundances of each element
        in the plasma.

    number_densities: `dict`, optional, keyword-only
        The number densities of elements (including both neutral atoms
        and ions) in units of inverse volume.

    n: ~astropy.units.Quantity, optional, keyword-only
        The number density scaling factor.  The number density of an
        element will be the product of its abundance and `n`.

    kappa: optional, keyword-only
        The value of kappa for a kappa distribution function.

    Raises
    ------
    AtomicError
        # TODO: Describe exceptions

    Examples
    --------
    >>> from plasmapy.atomic import IonizationStates
    >>> solar_corona = IonizationStates(['H', 'He', 'Fe'])

    Notes
    -----
    No more than one of `abundances`, `log_abundances`, and
    `number_densities` may be specified.

    Collisional ionization equilibrium is based on atomic data that
    has relative errors of order 20%.

    """

    @check_quantity(
        T_e={"units": u.K, "none_shall_pass": True},
        n={"units": u.m ** -3, "none_shall_pass": True},
    )
    def __init__(
            self,
            inputs,
            *,
            T_e=None,
            equilibrate=None,
            abundances=None,
            log_abundances=None,
            n=None,
            tol=1e-15,
            kappa=None):
        """Instantiate a `~plasmapy.atomic.IonizationStates` instance."""

        self._pars = collections.defaultdict(lambda: None)
        self.T_e = T_e
        self.n = n

        self.tol = tol

        if isinstance(inputs, dict):
            self.ionic_fractions = inputs
        elif isinstance(inputs, (list, tuple)):
            self.ionic_fractions = inputs
        else:
            raise TypeError(f"{inputs} are invalid inputs.")

        self.abundances = abundances
        self.log_abundances = log_abundances

    def __str__(self) -> str:
        join_str = ", " if len(self.elements) <= 5 else ","
        return f"<IonizationStates for: {join_str.join(self.elements)}>"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def ionic_fractions(self):
        try:
            return self._ionic_fractions
        except AttributeError as exc:
            raise AttributeError("Ionic fractions were not set.") from exc

    @ionic_fractions.setter
    def ionic_fractions(self, inputs: Union[Dict, List, Tuple]):
        """Set the ionic fractions."""
        if isinstance(inputs, dict):
            original_keys = inputs.keys()

            ionfrac_types = {type(inputs[key]) for key in original_keys}
            if u.Quantity in ionfrac_types and len(ionfrac_types) != 1:
                raise TypeError(
                    "Ionic fraction information may only be inputted "
                    "as a Quantity object if all ionic fractions are "
                    "Quantity arrays with units of inverse volume.")

            # Create a dictionary of Particle instances
            particles = dict()
            for key in original_keys:
                try:
                    particles[key] = key if isinstance(key, Particle) else Particle(key)
                except (InvalidParticleError, TypeError) as exc:
                    raise AtomicError(
                        f"Unable to create IonizationStates instance "
                        f"because {key} is not a valid particle") from exc

            # The particles whose ionization states are to be recorded
            # should be elements or isotopes but not ions or neutrals.

            is_element = particles[key].is_category('element')
            has_charge_info = particles[key].is_category(any_of=["charged", "uncharged"])

            if not is_element or has_charge_info:
                raise AtomicError(
                    f"{key} is not an element or isotope without "
                    f"charge information.")

            # We are sorting the elements/isotopes by atomic number and
            # mass number since we will often want to plot and analyze
            # things and this is the most sensible order.

            sorted_keys = sorted(original_keys, key=lambda k: (
                particles[k].atomic_number,
                particles[k].mass_number if particles[k].isotope else 0,
            ))

            _elements = []
            _particles = []
            new_ionic_fractions = {}

            for key in sorted_keys:
                new_key = particles[key].particle
                _particles.append(particles[key])
                if new_key in _elements:
                    raise AtomicError("Repeated particles in IonizationStates.")

                _elements.append(new_key)
                if isinstance(inputs[key], u.Quantity):
                    try:
                        number_densities = inputs[key].to(u.m ** -3)
                        n_elem = np.sum(number_densities)
                        new_ionic_fractions[new_key] = np.array(number_densities / n_elem)
                    except u.UnitConversionError as exc:
                        raise AtomicError("Units are not inverse volume.") from exc
                elif isinstance(inputs[key], np.ndarray) and inputs[key].dtype.kind == 'f':
                    new_ionic_fractions[particles[key].particle] = inputs[key]
                else:
                    try:
                        new_ionic_fractions[particles[key].particle] = \
                            np.array(inputs[key], dtype=np.float)
                    except ValueError as exc:
                        raise AtomicError(f"Inappropriate ionic fractions for {key}.") from exc

            for key in _elements:
                if np.min(new_ionic_fractions[key]) < 0 or np.max(new_ionic_fractions[key]) > 1:
                    raise AtomicError(f"Ionic fractions for {key} are not between 0 and 1.")
                if not np.isclose(np.sum(new_ionic_fractions[key]), 1, atol=self.tol, rtol=0):
                    raise AtomicError(f"Ionic fractions for {key} are not normalized to 1.")

        elif isinstance(inputs, (list, tuple)):

            try:
                _particles = [Particle(particle) for particle in inputs]
            except (InvalidParticleError, TypeError) as exc:
                raise AtomicError("Invalid inputs to IonizationStates") from exc

            _particles.sort(key=lambda p: (p.atomic_number, p.mass_number if p.isotope else 0))
            _elements = [particle.particle for particle in _particles]
            new_ionic_fractions = {
                particle.particle: np.full(
                    particle.atomic_number + 1,
                    fill_value=np.nan,
                    dtype=np.float64
                ) for particle in _particles
            }
        else:
            raise TypeError("Incorrect inputs to set ionic_fractions.")

        # Because this depends on _particles being sorted, we add in an
        # easy check that atomic numbers do not decrease.
        for i in range(1, len(_particles)):
            if _particles[i - 1].element == _particles[i].element:
                if not _particles[i - 1].isotope and _particles[i].isotope:
                    raise AtomicError("Cannot have an element and isotopes of that element.")
            elif _particles[i - 1].atomic_number > _particles[i].atomic_number:
                raise AtomicError("_particles has not been sorted.")

        self._particles = _particles
        self._elements = _elements
        self._ionic_fractions = new_ionic_fractions

    def __getitem__(self, *values):

        errmsg = f"Invalid indexing for IonizationStates instance: {values[0]}"

        one_input = not isinstance(values[0], tuple)
        two_inputs = len(values[0]) == 2

        if not one_input and not two_inputs:
            raise TypeError(errmsg)

        try:
            arg1 = values[0] if one_input else values[0][0]
            int_charge = None if one_input else values[0][1]
            particle = arg1 if arg1 in self.elements else particle_symbol(arg1)

            if int_charge is None:
                return IonizationState(
                    particle=particle,
                    ionic_fractions=self.ionic_fractions[particle],
                    T_e=self._pars["T_e"],
                    tol=self.tol,
                )
            else:
                if not isinstance(int_charge, numbers.Integral):
                    raise TypeError(f"{int_charge} is not a valid charge for {particle}.")
                elif not 0 <= int_charge <= atomic_number(particle):
                    raise ChargeError(f"{int_charge} is not a valid charge for {particle}.")
                return State(
                    integer_charge=int_charge,
                    ionic_fraction=self.ionic_fractions[particle][int_charge],
                    ionic_symbol=particle,
                )
        except Exception as exc:
            raise AtomicError(errmsg) from exc

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            raise NotImplementedError("Dictionary assignment not implemented.")
        else:
            try:
                particle = particle_symbol(key)
                if particle not in self.elements:
                    raise AtomicError(
                        f"{key} is not one of the particles kept track of "
                        f"by this IonizationStates instance.")
                new_fractions = np.array(value, dtype=np.float64)
                if new_fractions.min() < 0 or new_fractions.max() > 1:
                    raise ValueError("Ionic fractions must be between 0 and 1.")
                if not np.isclose(np.sum(new_fractions), 1):
                    raise ValueError("Ionic fractions are not normalized.")
                if len(new_fractions) != atomic_number(particle) + 1:
                    raise ValueError(f"Incorrect size of ionic fraction array for {key}.")
                self._ionic_fractions[particle][:] = new_fractions[:]
            except Exception as exc:
                raise AtomicError(
                    f"Cannot set item for this IonizationStates "
                    f"instance for key = {repr(key)} and value = "
                    f"{repr(value)}")

    def __iter__(self):
        self._element_index = 0
        return self

    def __next__(self):
        if self._element_index < len(self.elements):
            particle = self.elements[self._element_index]
            result = IonizationState(
                particle,
                self.ionic_fractions[particle],
                T_e=self.T_e,
                tol=self.tol,
            )
            self._element_index += 1
            return result
        else:
            del self._element_index
            raise StopIteration

    def __eq__(self, other):
        """
        Test that the ionic fractions are approximately equal to
        another `~plasmapy.atomic.IonizationStates` instance.
        """
        # TODO: Should we check temperatures, densities, and other
        # parameters too?

        if not isinstance(other, IonizationStates):
            raise TypeError(
                "IonizationStates instance can only be compared with "
                "other IonizationStates instances.")

        if self.elements != other.elements:
            raise AtomicError

        tol = np.min([self.tol, other.tol])

        for element in self.elements:

            are_all_close = np.allclose(
                self.ionic_fractions[element],
                other.ionic_fractions[element],
                atol=tol,
                rtol=0,
            )

            if not are_all_close:
                return False

        return True

    @property
    def elements(self) -> List[str]:
        """
        Return a list of the elements whose ionization states are being
        kept track of.
        """
        return self._elements

    @elements.setter
    def elements(self, elems):
        if hasattr(self, "_elements"):
            raise AtomicError("Cannot change elements once they have been set.")
        else:
            self._elements = elems

    @property
    def abundances(self) -> Optional[Dict]:
        """
        Return the elemental abundances
        """

#        if self._pars['abundances'] is None:
#            raise AtomicError("No abundances are available.")
        return self._pars['abundances']

    @abundances.setter
    def abundances(self, abundances_dict: Optional[Dict]):
        """
        Set the elemental (or isotopic) abundances.  The elements and
        isotopes must be the same as or a superset of the elements whose
        ionization states are being tracked.
        """
        if abundances_dict is None:
            self._pars['abundances'] = None
        elif not isinstance(abundances_dict, dict):
            raise TypeError(
                f"The abundances argument {abundances_dict} must be a dict with elements "
                "or isotopes as keys and ")
        else:
            old_keys = abundances_dict.keys()
            try:
                new_keys_dict = {particle_symbol(old_key): old_key for old_key in old_keys}
            except Exception:
                raise AtomicError(
                    "The key {repr(old_key)} in the abundances "
                    "dictionary is not a valid element or isotope.")

            new_elements = new_keys_dict.keys()

            old_elements_set = set(self.elements)
            new_elements_set = set(new_elements)

            if old_elements_set > new_elements_set:
                raise AtomicError(
                    f"The abundances of the following particles are "
                    f"missing: {old_elements_set - new_elements_set}")

            new_abundances_dict = {}

            for element in new_elements:
                inputted_abundance = abundances_dict[new_keys_dict[element]]
                try:
                    inputted_abundance = float(inputted_abundance)
                except Exception:
                    raise TypeError

                if inputted_abundance < 0:
                    raise AtomicError(f"The abundance of {element} is negative.")
                new_abundances_dict[element] = inputted_abundance

            self._pars['abundances'] = new_abundances_dict

    @property
    def log_abundances(self) -> Optional[Dict]:
        if self._pars['abundances'] is not None:
            log_abundances_dict = {}
            for key in self.abundances.keys():
                log_abundances_dict[key] = np.log10(self.abundances[key])
            return log_abundances_dict
        else:
            raise AtomicError("No abundances are available.")

    @log_abundances.setter
    def log_abundances(self, value: Optional[Dict]):

        if value is not None:
            try:
                new_abundances_input = {}
                for key in value.keys():
                    new_abundances_input[key] = 10 ** value[key]
                self.abundances = new_abundances_input
            except Exception as exc:
                raise AtomicError("Invalid log_abundances.")

    @property
    def T_e(self):
        """Return the electron temperature."""
        return self._pars['T_e']

    @T_e.setter
    def T_e(self, electron_temperature):
        if electron_temperature is None:
            self._pars['T_e'] = None
        else:
            try:
                temp = electron_temperature.to(u.K, equivalencies=u.temperature_energy())
            except (AttributeError, u.UnitsError):
                raise AtomicError("Invalid electron temperature.")
            else:
                if temp < 0 * u.K:
                    raise AtomicError("The electron temperature cannot be negative.")
                self._pars['T_e'] = temp

    @property
    def kappa(self):
        return self._kappa

    @kappa.setter
    def kappa(self, value: ):

    def equilibrate(self, T_e=None, elements='all', kappa=None):
        """
        Set the ionic fractions to collisional ionization equilibrium.
        Not implemented.

        The electron temperature used to calculate the new equilibrium
        ionic fractions will be the argument `T_e`, if given. Otherwise,
        the

        The new equilibrium ionic fractions will correspond to the
        argument `T_e` (if it is given) or the

        , or to the attribute `T_e` if it is not
        given


        If the argument `T_e` is given, then the equilibrium ionic
        fractions will correspond to that value.  Otherwise, if the
        attribute `T_e` is set for this
        `~plasmapy.atomic.IonizationStates` instance, then the equi


        Parameters
        ----------
        T_e : ~astropy.units.Quantity, optional
            The electron temperature.

        elements : `list`, `tuple`, or `str`, optional
            The elements to be equilibrated. If `elements` is `'all'`
            (default), then all elements will be equilibrated.


        """
        raise NotImplementedError

    @property
    def tol(self) -> numbers.Real:
        """Return the absolute tolerance for comparisons."""
        return self._tol

    @tol.setter
    def tol(self, atol: numbers.Real):
        """Set the absolute tolerance for comparisons."""
        if not isinstance(atol, numbers.Real):
            raise TypeError("The attribute tol must be a real number.")
        if 0 <= atol <= 1.0:
            self._tol = atol
        else:
            raise ValueError("Need 0 <= tol <= 1.")

    def normalize(self):
        for particle in self.elements:
            tot = np.sum(self.ionic_fractions[particle])
            self.ionic_fractions[particle] = self.ionic_fractions[particle] / tot

    @property
    def number_densities(self) -> Dict:
        """
        Return a `dict` containing the number densities for element or
        isotope.
        """
        # TODO: Add tests!

        try:
            number_densities = {
                elem: self.n * self.abundances[elem] * self.ionic_fractions[elem]
                for elem in self.elements}
        except Exception as exc:
            raise AtomicError("Unable to calculate ionic number densities.") from exc
        return number_densities

    @property
    @u.quantity_input
    def n_e(self) -> u.m ** -3:
        """Return the electron number density, assuming quasineutrality."""

        number_densities = self.number_densities
        n_e = 0.0 * u.m ** -3

        for elem in self.elements:
            atomic_numb = atomic_number(elem)
            number_of_ionization_states = atomic_numb + 1
            integer_charges = np.linspace(0, atomic_numb, number_of_ionization_states)
            n_e += np.sum(number_densities[elem] * integer_charges)

        return n_e

    @property
    @u.quantity_input
    def n(self) -> u.m ** -3:
        """
        Return the number density scaling factor.
        """
        if 'H' not in self.elements or self._pars['n'] is None:
            raise AtomicError("The number density of hydrogen is not ")
        return self._pars['n']

    @n.setter
    def n(self, n: u.m ** -3):
        if n is None:
            self._pars['n'] = n
        else:
            try:
                self._pars['n'] = n.to(u.m ** -3)
            except u.UnitConversionError:
                raise AtomicError("Units cannot be converted to u.m**-3.")
            except Exception:
                raise AtomicError(f"{n} is not a valid number density.") from None
