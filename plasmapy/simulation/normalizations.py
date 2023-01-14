import astropy.units as u

from astropy.constants import k_B
from astropy.constants import mu0 as μ0
from numbers import Integral
from typing import Optional

from plasmapy.formulary import Alfven_speed
from plasmapy.particles import Particle, particle_input, ParticleLike
from plasmapy.particles.exceptions import ChargeError
from plasmapy.simulation.abstractions import AbstractNormalizations

_length = u.get_physical_type(u.m)
_magnetic_field = u.get_physical_type(u.T)
_time = u.get_physical_type(u.s)
_number_density = u.get_physical_type(u.m**-3)
_velocity = u.get_physical_type(u.m / u.s)


class MHDNormalizations(AbstractNormalizations):
    r"""
    A class containing the |normalization constants| for the equations
    of magnetohydrodynamics.

    This class assumes a two-component electron-ion plasma, where the
    |charge number| of the ion is :math:`Z`.

    Parameters
    ----------
    *quantities : `tuple` of |Quantity|
        Three normalization constants

    ion : |atom-like|
        The ion of the electron-ion plasma.

    Z : integer, optional
        The charge number of the ion. Must be positive.

    mass_numb : integer, optional
        The mass number of the isotope of the ion.

    Notes
    -----
    A |normalization constant| is a multiplicative factor that is used
    to transform a physical quantity into a dimensionless number and
    vice versa. For example, if we use the sound speed :math:`V_s` as
    the normalization for velocity, then the result will be the
    dimensionless :wikipedia:`Mach number`. Normalizations are often
    employed to provide a convenient reference value for the
    interpretation of data, to avoid calculations between very large and
    very small numbers in numerical simulations, and/or to simplify
    systems of equations for analytical theory or numerical solutions.

    This class represents the normalization coefficients of the
    equations of magnetohydrodynamics in SI units. We define :math:`n`
    as the number density, :math:`ρ` as mass density, :math:`\mathbf{B}`
    as the magnetic field, :math:`\mathbf{E}` as the electric field,
    :math:`\mathbf{V}` as the bulk plasma velocity, and
    :math:`\mathbf{J}` as the current density.



    The :wikipedia:`continuity equation` is:

    .. math::

        \frac{∂n}{∂t} + ∇ · \left( n \mathbf{V} \right) = 0.



    :wikipedia:`Ampere's law` without :wikipedia:`displacement current`
    is:

    .. math::

        μ_0 \mathbf{J} = ∇ × \mathbf{B}.

    :wikipedia:`Faraday's law` is: (trying out the mathematical bold
    unicode B on the left

    .. math::

        \frac{∂𝐁 \mathbf{B}}{∂t} = - ∇ × \mathbf{B}

    The generalized Ohm's law is:

    .. math::

        \mathbf{E} + \mathbf{V} × \mathbf{B}
        = η \mathbf{J} + \frac{\mathbf{J} × \mathbf{B}{n_e e}
        ,

    where :math:`e` is the :wikipedia:`elementary charge`.

    The momentum equation is:

    .. math::

        ρ \left( \frac{∂}{∂t} + \mathbf{V} · ∇ \right) \mathbf{V}
        = \mathbf{J} × \mathbf{B} - ∇ p

    Examples
    --------
    >>> import astropy.units as u
    >>> from plasmapy.simulation import MHDNormalizations
    >>> n0 = 1e19 * u.m**-3
    >>> L0 = 1 * u.km
    >>> B0 = 10 * u.G
    >>> normalizations = MHDNormalizations("p+", n0, L0, B0)
    >>> normalizations.ion
    Particle("p+")
    >>> normalizations.number_density
    <Quantity 1.e+19 1 / m3>
    >>> normalizations.magnetic_field
    <Quantity 0.001 T>
    >>> normalizations.length
    <Quantity 1000. m>
    """

    @particle_input
    def __init__(
        self,
        *quantities,
        ion: ParticleLike,
        Z: Optional[Integral] = None,
        mass_numb: Optional[Integral] = None
    ):
        if ion.charge_number <= 0:
            raise ChargeError("The charge of the ion must be positive.")

        self._ion = ion

    @property
    def acceleration(self) -> u.m * u.s**-2:
        r"""
        The |normalization constant| for acceleration,

        .. math::

           a_⭑ ≡ \frac{L_⭑}{t_⭑^2}.

        Returns
        -------
        |Quantity|
        """
        return self.length / self.time**2

    @property
    def area(self) -> u.m**2:
        r"""
        The |normalization constant| for area,

        .. math::

           A_⋆ ≡ L_⋆^2
        """
        return self.length**2

    @property
    def current_density(self) -> u.A * u.m**-2:
        r"""
        The |normalization constant| for :wikipedia:`current density`,

        .. math::

           J_⭑ ≡ \frac{B_⭑}{μ_0 L_⭑}.

        Returns
        -------
        |Quantity|
        """
        return self.magnetic_field / (μ0 * self.length)

    @property
    def diffusivity(self) -> u.m**2 / u.s:
        r"""
        The |normalization constant| for :wikipedia:`diffusivity`,

        .. math:

           D_⭑ ≡ \frac{L_⭑^2}{t_⭑}

        Returns
        -------
        |Quantity|
        """
        return self.length**2 / self.time

    @property
    def dynamic_viscosity(self) -> u.Pa * u.s:
        r"""
        The |normalization constant| for :wikipedia:`dynamic viscosity`,

        .. math::

           μ_⭑ ≡ p_⭑ t_⭑

        .. danger::

           Verify this!

        Returns
        -------
        |Quantity|

        Notes
        -----
        For `kinematic viscosity`_, use
        ~`plasmapy.simulation.abstractions.MHDNormalizations.diffusivity`.

        .. _kinematic viscosity: https://en.wikipedia.org/wiki/Viscosity#Kinematic_viscosity
        """
        return self.pressure * self.time

    @property
    def electric_field(self) -> u.V / u.m:
        """
        The |normalization constant| for electric field,

        .. math::

           E_⭑ ≡ V_⭑ B_⭑.

        Returns
        -------
        |Quantity|
        """
        return self.velocity * self.magnetic_field

    @property
    def energy(self) -> u.J:
        """
        The |normalization constant| for energy,

           e_⋆ ≡ \frac{m_⋆ L_⋆^2}{t_⋆^2}

        .. danger::

           Verify this!

        Returns
        -------
        |Quantity|
        """
        return ...

    @property
    def frequency(self) -> u.s**-1:
        """
        The |normalization constant| for frequency,

        .. math::

           f_⭑ ≡ t_⭑^{-1}.

        .. danger::

           Clear up whether this related to regular frequency vs angular
           frequency.

        Returns
        -------
        |Quantity|
        """
        return u.time**-1

    @property
    def heat_flux(self) -> u.J * u.m**-2 * u.s**-1:
        r"""
        The heat flux :term:`normalization`,

        .. math::

           q_⭑ ≡ \frac{n_⋆ e_⋆ L_⋆}{t_⋆}.

        .. danger::

           Verify this!

        Returns
        -------
        |Quantity|
        """
        return ...

    @property
    def ion(self) -> Particle:
        """
        The ion in the plasma.

        Returns
        -------
        |Particle|
        """
        return self._ion

    @property
    def length(self) -> u.m:
        r"""
        The length :term:`normalization`, :math:`L_⭑`\ .

        Returns
        -------
        |Quantity|
        """
        return self._length

    @property
    def magnetic_field(self) -> u.T:
        r"""
        The magnetic field :term:`normalization`, :math:`B_⭑`\ .

        Returns
        -------
        |Quantity|
        """
        return self._magnetic_field

    @property
    def magnetic_flux(self) -> u.Wb:
        r"""
        The magnetic flux :term:`normalization`,

        .. math::

           Φ_⋆ ≡ B_⋆ A_⋆.

        Returns
        -------
        |Quantity|
        """
        return self.magnetic_field * self.area

    @property
    def mass(self) -> u.kg:
        r"""
        The |normalization constant| for mass,

        .. math::

           m_⭑ ≡ m_i + Z m_e,

        where :math:`m_i` is the ion mass, :math:`m_e` is the electron
        mass, and :math:`Z` is the charge number of the ion.

        .. danger::

           Verify this!

        Returns
        -------
        |Quantity|
        """
        raise NotImplementedError

    @property
    def mass_density(self) -> u.kg * u.m**-3:
        r"""
        The |normalization constant| for mass density,

        .. math::

           ρ_⋆ ≡ m_⋆ n_⋆.

        .. danger::

           How do we get :math:`m_⋆`\ ?

        Returns
        -------
        |Quantity|
        """
        raise NotImplementedError

    @property
    def number_density(self) -> u.m**-3:
        r"""
        The |normalization constant| for number density, :math:`n_⭑`.

        Returns
        -------
        |Quantity|
        """
        return self._quantities[_number_density]

    @property
    def pressure(self):
        r"""
        The |normalization constant| for pressure,

        .. math::

           p_⭑ ≡ \frac{B_⭑^2}{μ_0}.

        Returns
        -------
        |Quantity|
        """
        return self.magnetic_field**2 / μ0

    @property
    def resistivity(self) -> u.ohm * u.m:
        r"""
        The |normalization constant| for resistivity,

        .. math::

           η_⭑ ≡ μ_0 L_⭑ V_⭑.

        Returns
        -------
        |Quantity|
        """
        return μ0 * self.length

    @property
    def temperature(self) -> u.K:
        r"""
        The temperature :term:`normalization`,

        .. math::

           T_⭑ ≡ \frac{B_⭑^2}{k_B μ_0 n_⭑}.

        Returns
        -------
        |Quantity|
        """
        return self.magnetic_field**2 / (k_B * μ0 * self.number_density)

    @property
    def thermal_conductivity(self) -> u.W * u.K**-1 * u.m**-1:
        r"""
        The thermal conduction :term:`normalization`,

        .. math::

           _⭑ ≡

        Returns
        -------
        |Quantity|
        """
        return ...

    @property
    def time(self) -> u.s:
        r"""
        The time :term:`normalization`,

        t_⭑ ≡ \frac{L_⭑}{V_⭑}.

        Returns
        -------
        |Quantity|
        """
        return self.length / self.velocity

    @property
    def velocity(self) -> u.m / u.s:
        r"""
        The velocity :term:`normalization`,

        .. math::

           V_⭑ ≡ \frac{B_⭑}{\sqrt{μ_0 ρ_⭑}}.

        Returns
        -------
        |Quantity|
        """
        return Alfven_speed(B=self.magnetic_field, density=self.mass_density)

    @property
    def wavenumber(self) -> u.m**-1:
        r"""
        The wavenumber :term:`normalization`,

        .. math::

           k_⭑ ≡ \frac{1}{L_⭑}
        """
