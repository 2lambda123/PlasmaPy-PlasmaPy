"""
Defines the Thomson scattering analysis module as
part of the diagnostics package.
"""

__all__ = [
    "spectral_density",
    "spectral_density_model",
]

import astropy.constants as const
import astropy.units as u
import numbers
import numpy as np
import re
import warnings

from lmfit import Model
from typing import Any, Dict, List, Tuple, Union

from plasmapy.formulary.dielectric import permittivity_1D_Maxwellian
from plasmapy.formulary.frequencies import plasma_frequency
from plasmapy.formulary.speeds import thermal_speed, thermal_speed_coefficients
from plasmapy.particles import Particle, particle_mass
from plasmapy.utils.decorators import (
    bind_lite_func,
    preserve_signature,
    validate_quantities,
)

c_si_unitless = const.c.si.value
e_si_unitless = const.e.si.value
m_p_si_unitless = const.m_p.si.value
m_e_si_unitless = const.m_e.si.value


# TODO: interface for inputting a multi-species configuration could be
#     simplified using the plasmapy.classes.plasma_base class if that class
#     included ion and electron drift velocities and information about the ion
#     atomic species.


@preserve_signature
def spectral_density_lite(
    wavelengths,
    probe_wavelength: numbers.Real,
    n: numbers.Real,
    Te: np.ndarray,
    Ti: np.ndarray,
    efract: np.ndarray = None,
    ifract: np.ndarray = None,
    ion_z: np.ndarray = None,
    ion_mass: np.ndarray = None,
    electron_vel: np.ndarray = None,
    ion_vel: np.ndarray = None,
    probe_vec: np.ndarray = None,
    scatter_vec: np.ndarray = None,
    instr_func_arr: np.ndarray = None,
) -> Tuple[Union[np.floating, np.ndarray], np.ndarray]:

    r"""

    The ":term:`lite-function`" version of
    `~plasmapy.formulary.parameters.thermal_speed`.  Performs the same
    thermal speed calculations as
    `~plasmapy.formulary.parameters.thermal_speed`, but is intended for
    computational use and, thus, has data conditioning safeguards
    removed.


    Parameters
    ----------

    wavelengths : `~numpy.ndarray`, shape (Nwavelengths,)
        Array of wavelengths in meters over which the spectral density function
        will be calculated.

    probe_wavelength : real number
        Wavelength of the probe laser in meters.

    n : real number
        Mean (0th order) density of all plasma components combined in m^-3.

    Te : `~numpy.ndarray`, shape (Ne, )
        Temperature of each electron component in Kelvin. Shape (Ne, ) must be
        equal to the number of electron populations Ne.

    Ti : `~numpy.ndarray`, shape (Ni, )
        Temperature of each ion component in Kelvin. Shape (Ni, ) must be
        equal to the number of ion populations Ni.

    efract : `~numpy.ndarray`, shape (Ne, ), optional
        An np.ndarray where each element represents the fraction (or ratio)
        of the electron population number density to the total electron number density.
        Must sum to 1.0. Default is a single electron component.

    ifract : `~numpy.ndarray`, shape (Ni, ), optional
        An np.ndarray object where each element represents the fraction (or ratio)
        of the ion population number density to the total ion number density.
        Must sum to 1.0. Default is a single ion species.

    ion_z : `~numpy.ndarray`, shape (Ni,), optional
        An np.ndarray of the charge number Z of each ion species.

    ion_mass : `~numpy.ndarray`, shape (Ni,), optional
        An np.ndarray of the mass of each ion species in kg.

    electron_vel : `~numpy.ndarray`, shape (Ne, 3), optional
        Velocity of each electron population in the rest frame (in m/s).
        If set, overrides electron_vdir and electron_speed.
        Defaults to a stationary plasma [0, 0, 0] m/s.

    ion_vel : `~numpy.ndarray`, shape (Ni, 3), optional
        Velocity vectors for each electron population in the rest frame
        (in  m/s). If set, overrides ion_vdir and ion_speed.
        Defaults zero drift for all specified ion species.

    probe_vec : float `~numpy.ndarray`, shape (3, )
        Unit vector in the direction of the probe laser. Defaults to
        ``[1, 0, 0]``.

    scatter_vec : float `~numpy.ndarray`, shape (3, )
        Unit vector pointing from the scattering volume to the detector.
        Defaults to [0, 1, 0] which, along with the default `probe_vec`,
        corresponds to a 90 degree scattering angle geometry.

    instr_func_arr : `~numpy.ndarray`, shape (Nwavelengths,) optional

        The insturment function evaluated at a linearly spaced range of
        wavelengths ranging from :math:`-W` to :math:`W`, where

        .. math::
            W = 0.5*(\text(Max)(\lambda) - \text(Min)(\lambda))

        Where :math:`\lambda` is the wavelengths array. This array will be
        convolved with the spectral density function
        before it is returned.


    Returns
    -------
    alpha : float
        Mean scattering parameter, where `alpha` > 1 corresponds to collective
        scattering and `alpha` < 1 indicates non-collective scattering. The
        scattering parameter is calculated based on the total plasma density n.

    Skw : `~numpy.ndarray`
        Computed spectral density function over the input `wavelengths` array
        with units of s/rad.


    """

    if efract is None:
        efract = np.array([1.0])

    if ifract is None:
        ifract = np.array([1.0])

    if ion_z is None:
        ion_z = np.array([1])

    if ion_mass is None:
        ion_mass = np.array([1])

    if probe_vec is None:
        probe_vec = np.array([1, 0, 0])

    if scatter_vec is None:
        scatter_vec = np.array([0, 1, 0])

    if electron_vel is None:
        electron_vel = np.zeros([efract.size, 3])

    if ion_vel is None:
        ion_vel = np.zeros([ifract.size, 3])

    scattering_angle = np.arccos(np.dot(probe_vec, scatter_vec))

    # Calculate plasma parameters
    # Temperatures here in K!
    coefs = thermal_speed_coefficients("most_probable", 3)
    vTe = thermal_speed.lite(Te, m_e_si_unitless, coefs)
    vTi = thermal_speed.lite(Ti, ion_mass, coefs)
    zbar = np.sum(ifract * ion_z)

    # Compute electron and ion densities
    ne = efract * n
    ni = ifract * n / zbar  # ne/zbar = sum(ni)

    # wpe is calculated for the entire plasma (all electron populations combined)
    wpe = plasma_frequency.lite(n, m_e_si_unitless, 1)

    # Convert wavelengths to angular frequencies (electromagnetic waves, so
    # phase speed is c)
    ws = 2 * np.pi * c_si_unitless / wavelengths
    wl = 2 * np.pi * c_si_unitless / probe_wavelength

    # Compute the frequency shift (required by energy conservation)
    w = ws - wl

    # Compute the wavenumbers in the plasma
    # See Sheffield Sec. 1.8.1 and Eqs. 5.4.1 and 5.4.2
    ks = np.sqrt(ws ** 2 - wpe ** 2) / c_si_unitless
    kl = np.sqrt(wl ** 2 - wpe ** 2) / c_si_unitless

    # Compute the wavenumber shift (required by momentum conservation)\
    # Eq. 1.7.10 in Sheffield
    k = np.sqrt(ks ** 2 + kl ** 2 - 2 * ks * kl * np.cos(scattering_angle))
    # Normal vector along k
    k_vec = scatter_vec - probe_vec
    k_vec = k_vec / np.linalg.norm(k_vec)

    # Compute Doppler-shifted frequencies for both the ions and electrons
    # Matmul is simultaneously conducting dot product over all wavelengths
    # and ion components
    w_e = w - np.matmul(electron_vel, np.outer(k, k_vec).T)
    w_i = w - np.matmul(ion_vel, np.outer(k, k_vec).T)

    # Compute the scattering parameter alpha
    # expressed here using the fact that v_th/w_p = root(2) * Debye length
    alpha = np.sqrt(2) * wpe / np.outer(k, vTe)

    # Calculate the normalized phase velocities (Sec. 3.4.2 in Sheffield)
    xe = np.outer(1 / vTe, 1 / k) * w_e
    xi = np.outer(1 / vTi, 1 / k) * w_i

    # Calculate the susceptibilities
    chiE = np.zeros([efract.size, w.size], dtype=np.complex128)
    for i, fract in enumerate(efract):
        wpe = plasma_frequency.lite(ne[i], m_e_si_unitless, 1)
        chiE[i, :] = permittivity_1D_Maxwellian.lite(w_e[i, :], k, vTe[i], wpe)

    # Treatment of multiple species is an extension of the discussion in
    # Sheffield Sec. 5.1
    chiI = np.zeros([ifract.size, w.size], dtype=np.complex128)
    for i, fract in enumerate(ifract):
        wpi = plasma_frequency.lite(ni[i], ion_mass[i], ion_z[i])
        chiI[i, :] = permittivity_1D_Maxwellian.lite(w_i[i, :], k, vTi[i], wpi)

    # Calculate the longitudinal dielectric function
    epsilon = 1 + np.sum(chiE, axis=0) + np.sum(chiI, axis=0)

    econtr = np.zeros([efract.size, w.size], dtype=np.complex128)
    for m in range(efract.size):
        econtr[m, :] = efract[m] * (
            2
            * np.sqrt(np.pi)
            / k
            / vTe[m]
            * np.power(np.abs(1 - np.sum(chiE, axis=0) / epsilon), 2)
            * np.exp(-xe[m, :] ** 2)
        )

    icontr = np.zeros([ifract.size, w.size], dtype=np.complex128)
    for m in range(ifract.size):
        icontr[m, :] = ifract[m] * (
            2
            * np.sqrt(np.pi)
            * ion_z[m]
            / k
            / vTi[m]
            * np.power(np.abs(np.sum(chiE, axis=0) / epsilon), 2)
            * np.exp(-xi[m, :] ** 2)
        )

    # Recast as real: imaginary part is already zero
    Skw = np.real(np.sum(econtr, axis=0) + np.sum(icontr, axis=0))

    # Apply an insturment function if one is provided
    if instr_func_arr is not None:
        Skw = np.convolve(Skw, instr_func_arr, mode="same")
    return np.mean(alpha), Skw


@validate_quantities(
    wavelengths={"can_be_negative": False, "can_be_zero": False},
    probe_wavelength={"can_be_negative": False, "can_be_zero": False},
    n={"can_be_negative": False, "can_be_zero": False},
    Te={"can_be_negative": False, "equivalencies": u.temperature_energy()},
    Ti={"can_be_negative": False, "equivalencies": u.temperature_energy()},
)
@bind_lite_func(spectral_density_lite)
def spectral_density(
    wavelengths: u.nm,
    probe_wavelength: u.nm,
    n: u.m ** -3,
    Te: u.K,
    Ti: u.K,
    efract: np.ndarray = None,
    ifract: np.ndarray = None,
    ion_species: Union[str, List[str], Particle, List[Particle]] = "p",
    electron_vel: u.m / u.s = None,
    ion_vel: u.m / u.s = None,
    probe_vec=None,
    scatter_vec=None,
    instr_func=None,
) -> Tuple[Union[np.floating, np.ndarray], np.ndarray]:
    r"""
    Calculate the spectral density function for Thomson scattering of a
    probe laser beam by a multi-species Maxwellian plasma.

    This function calculates the spectral density function for Thomson
    scattering of a probe laser beam by a plasma consisting of one or more ion
    species and a one or more thermal electron populations (the entire plasma
    is assumed to be quasi-neutral)

    .. math::
        S(k,\omega) = \sum_e \frac{2\pi}{k}
        \bigg |1 - \frac{\chi_e}{\epsilon} \bigg |^2
        f_{e0,e} \bigg (\frac{\omega}{k} \bigg ) +
        \sum_i \frac{2\pi Z_i}{k}
        \bigg |\frac{\chi_e}{\epsilon} \bigg |^2 f_{i0,i}
        \bigg ( \frac{\omega}{k} \bigg )

    where :math:`\chi_e` is the electron component susceptibility of the
    plasma and :math:`\epsilon = 1 + \sum_e \chi_e + \sum_i \chi_i` is the total
    plasma dielectric  function (with :math:`\chi_i` being the ion component
    of the susceptibility), :math:`Z_i` is the charge of each ion, :math:`k`
    is the scattering wavenumber, :math:`\omega` is the scattering frequency,
    and :math:`f_{e0,e}` and :math:`f_{i0,i}` are the electron and ion velocity
    distribution functions respectively. In this function the electron and ion
    velocity distribution functions are assumed to be Maxwellian, making this
    function equivalent to Eq. 3.4.6 in `Sheffield`_.

    Parameters
    ----------

    wavelengths : `~astropy.units.Quantity`
        Array of wavelengths over which the spectral density function
        will be calculated. (convertible to nm)

    probe_wavelength : `~astropy.units.Quantity`
        Wavelength of the probe laser. (convertible to nm)

    n : `~astropy.units.Quantity`
        Mean (0th order) density of all plasma components combined.
        (convertible to cm^-3.)

    Te : `~astropy.units.Quantity`, shape (Ne, )
        Temperature of each electron component. Shape (Ne, ) must be equal to the
        number of electron populations Ne. (in K or convertible to eV)

    Ti : `~astropy.units.Quantity`, shape (Ni, )
        Temperature of each ion component. Shape (Ni, ) must be equal to the
        number of ion populations Ni. (in K or convertible to eV)

    efract : array_like, shape (Ne, ), optional
        An array-like object where each element represents the fraction (or ratio)
        of the electron population number density to the total electron number density.
        Must sum to 1.0. Default is a single electron component.

    ifract : array_like, shape (Ni, ), optional
        An array-like object where each element represents the fraction (or ratio)
        of the ion population number density to the total ion number density.
        Must sum to 1.0. Default is a single ion species.

    ion_species : str or `~plasmapy.particles.Particle`, shape (Ni, ), optional
        A list or single instance of `~plasmapy.particles.Particle`, or strings
        convertible to `~plasmapy.particles.Particle`. Default is ``'H+'``
        corresponding to a single species of hydrogen ions.

    electron_vel : `~astropy.units.Quantity`, shape (Ne, 3), optional
        Velocity of each electron population in the rest frame. (convertible to m/s)
        If set, overrides electron_vdir and electron_speed.
        Defaults to a stationary plasma [0, 0, 0] m/s.

    ion_vel : `~astropy.units.Quantity`, shape (Ni, 3), optional
        Velocity vectors for each electron population in the rest frame
        (convertible to m/s). If set, overrides ion_vdir and ion_speed.
        Defaults zero drift for all specified ion species.

    probe_vec : float `~numpy.ndarray`, shape (3, )
        Unit vector in the direction of the probe laser. Defaults to
        ``[1, 0, 0]``.

    scatter_vec : float `~numpy.ndarray`, shape (3, )
        Unit vector pointing from the scattering volume to the detector.
        Defaults to [0, 1, 0] which, along with the default `probe_vec`,
        corresponds to a 90 degree scattering angle geometry.

    instr_func : function
        A function representing the instrument function that takes an `~astropy.units.Quantity`
        of wavelengths (centered on zero) and returns the instrument point
        spread function. The resulting array will be convolved with the
        spectral density function before it is returned.

    Returns
    -------
    alpha : float
        Mean scattering parameter, where `alpha` > 1 corresponds to collective
        scattering and `alpha` < 1 indicates non-collective scattering. The
        scattering parameter is calculated based on the total plasma density n.

    Skw : `~astropy.units.Quantity`
        Computed spectral density function over the input `wavelengths` array
        with units of s/rad.

    Notes
    -----

    For details, see "Plasma Scattering of Electromagnetic Radiation" by
    Sheffield et al. `ISBN 978\\-0123748775`_. This code is a modified version
    of the program described therein.

    For a concise summary of the relevant physics, see Chapter 5 of Derek
    Schaeffer's thesis, DOI: `10.5281/zenodo.3766933`_.

    .. _`ISBN 978\\-0123748775`: https://www.sciencedirect.com/book/9780123748775/plasma-scattering-of-electromagnetic-radiation
    .. _`10.5281/zenodo.3766933`: https://doi.org/10.5281/zenodo.3766933
    .. _`Sheffield`: https://doi.org/10.1016/B978-0-12-374877-5.00003-8
    """

    # Validate efract
    if efract is None:
        efract = np.ones(1)
    else:
        efract = np.asarray(efract, dtype=np.float64)

    # Validate ifract
    if ifract is None:
        ifract = np.ones(1)
    else:
        ifract = np.asarray(ifract, dtype=np.float64)

    if probe_vec is None:
        probe_vec = np.array([1, 0, 0])

    if scatter_vec is None:
        scatter_vec = np.array([0, 1, 0])

    # If electron velocity is not specified, create an array corresponding
    # to zero drift
    if electron_vel is None:
        electron_vel = np.zeros([efract.size, 3]) * u.m / u.s

    # Condition the electron velocity keywords
    if ion_vel is None:
        ion_vel = np.zeros([ifract.size, 3]) * u.m / u.s

    # Condition ion_species
    if isinstance(ion_species, (str, Particle)):
        ion_species = [ion_species]
    if len(ion_species) == 0:
        raise ValueError("At least one ion species needs to be defined.")
    for ii, ion in enumerate(ion_species):
        if isinstance(ion, Particle):
            continue
        ion_species[ii] = Particle(ion)

    # Condition Ti
    if Ti.size == 1:
        # If a single quantity is given, put it in an array so it's iterable
        # If Ti.size != len(ion_species), assume same temp. for all species
        Ti = (
            np.array(
                [
                    Ti.value,
                ]
            )
            * Ti.unit
        )

    # Make sure the sizes of ion_species, ifract, ion_vel, and Ti all match
    if (
        (len(ion_species) != ifract.size)
        or (ion_vel.shape[0] != ifract.size)
        or (Ti.size != ifract.size)
    ):
        raise ValueError(
            f"Inconsistent number of ion species in ifract ({ifract}), "
            f"ion_species ({len(ion_species)}), Ti ({Ti.size}), "
            f"and/or ion_vel ({ion_vel.shape[0]})."
        )

    # Condition Te
    if Te.size == 1:
        # If a single quantity is given, put it in an array so it's iterable
        # If Te.size != len(efract), assume same temp. for all species
        Te = (
            np.array(
                [
                    Te.value,
                ]
            )
            * Te.unit
        )

    # Make sure the sizes of efract, electron_vel, and Te all match
    if (electron_vel.shape[0] != efract.size) or (Te.size != efract.size):
        raise ValueError(
            f"Inconsistent number of electron populations in efract ({efract.size}), "
            f"Te ({Te.size}), or electron velocity ({electron_vel.shape[0]})."
        )

    # Create arrays of ion Z and mass from particles given
    ion_z = np.zeros(len(ion_species))
    ion_mass = np.zeros(len(ion_species)) * u.kg
    for i, particle in enumerate(ion_species):
        ion_z[i] = particle.charge_number
        ion_mass[i] = particle_mass(particle)

    probe_vec = probe_vec / np.linalg.norm(probe_vec)
    scatter_vec = scatter_vec / np.linalg.norm(scatter_vec)

    # Apply the insturment function
    if instr_func is not None and callable(instr_func):

        # Create an array of wavelengths of the same size as wavelengths
        # but centered on zero
        wspan = (np.max(wavelengths) - np.min(wavelengths)) / 2
        eval_w = np.linspace(-wspan, wspan, num=wavelengths.size)
        instr_func_arr = instr_func(eval_w)

        if type(instr_func_arr) != np.ndarray:
            raise ValueError(
                "instr_func must be a function that returns a "
                "np.ndarray, but the provided function returns "
                f" a {type(instr_func_arr)}"
            )

        if wavelengths.shape != instr_func_arr.shape:
            raise ValueError(
                "The shape of the array returned from the "
                f"instr_func ({instr_func_arr.shape}) "
                "does not match the shape of the wavelengths "
                f"array ({wavelengths.shape})."
            )

        instr_func_arr *= 1 / np.sum(instr_func_arr)
    else:
        instr_func_arr = None

    alpha, Skw = spectral_density_lite(
        wavelengths.to(u.m).value,
        probe_wavelength.to(u.m).value,
        n.to(u.m ** -3).value,
        Te.to(u.K).value,
        Ti.to(u.K).value,
        efract=efract,
        ifract=ifract,
        ion_z=ion_z,
        ion_mass=ion_mass.to(u.kg).value,
        ion_vel=ion_vel.to(u.m / u.s).value,
        electron_vel=electron_vel.to(u.m / u.s).value,
        probe_vec=probe_vec,
        scatter_vec=scatter_vec,
        instr_func_arr=instr_func_arr,
    )

    return alpha, Skw * u.s / u.rad


# ***************************************************************************
# These functions are necessary to interface scalar Parameter objects with
# the array inputs of spectral_density
# ***************************************************************************


def _count_populations_in_params(params: Dict[str, Any], prefix: str) -> int:
    """
    Counts the number of electron or ion populations in a ``params`` `dict`.

    The number of populations is determined by counting the number of items in
    the ``params`` `dict` with a key that starts with the string defined by
    ``prefix``.
    """
    return len([key for key in params if key.startswith(prefix)])


def _params_to_array(
    params: Dict[str, Any], prefix: str, vector: bool = False
) -> np.ndarray:
    """
    Constructs an array from the values contained in the dictionary
    ``params`` associated with keys starting with the prefix defined
    by ``prefix``.

    If ``vector == False``, then values for keys matching the
    expression `prefix_[0-9]+` are gathered into a 1D array.

    If ``vector == True``, then values for keys matching the
    expression `prefix_[xyz]_[0-9]+` are gathered into a 2D array of
    shape ``(N, 3)``.

    Notes
    -----
    This function allows `lmfit.parameter.Parameter` inputs to be
    converted into the array-type inputs required by the spectral
    density function.

    """

    if vector:
        npop = _count_populations_in_params(params, prefix + "_x")
        output = np.zeros([npop, 3])
        for i in range(npop):
            for j, ax in enumerate(["x", "y", "z"]):
                output[i, j] = params[prefix + f"_{ax}_{i}"].value

    else:
        npop = _count_populations_in_params(params, prefix)
        output = np.zeros([npop])
        for i in range(npop):
            output[i] = params[prefix + f"_{i}"]

    return output


# ***************************************************************************
# Fitting functions
# ***************************************************************************


def _spectral_density_model(wavelengths, settings=None, **params):
    """
    lmfit Model function for fitting Thomson spectra

    For descriptions of arguments, see the `thomson_model` function.

    """

    # LOAD FROM SETTINGS
    ion_z = settings["ion_z"]
    ion_mass = settings["ion_mass"]
    probe_vec = settings["probe_vec"]
    scatter_vec = settings["scatter_vec"]
    electron_vdir = settings["electron_vdir"]
    ion_vdir = settings["ion_vdir"]
    probe_wavelength = settings["probe_wavelength"]
    instr_func_arr = settings["instr_func_arr"]

    # LOAD FROM PARAMS
    n = params["n"]
    Te = _params_to_array(params, "Te")
    Ti = _params_to_array(params, "Ti")
    efract = _params_to_array(params, "efract")
    ifract = _params_to_array(params, "ifract")

    electron_speed = _params_to_array(params, "electron_speed")
    ion_speed = _params_to_array(params, "ion_speed")

    electron_vel = electron_speed[:, np.newaxis] * electron_vdir
    ion_vel = ion_speed[:, np.newaxis] * ion_vdir

    # Convert temperatures from eV to Kelvin (required by fast_spectral_density)
    Te *= 11605
    Ti *= 11605

    alpha, model_Skw = spectral_density.lite(
        wavelengths,
        probe_wavelength,
        n,
        Te,
        Ti,
        efract=efract,
        ifract=ifract,
        ion_z=ion_z,
        ion_mass=ion_mass,
        electron_vel=electron_vel,
        ion_vel=ion_vel,
        probe_vec=probe_vec,
        scatter_vec=scatter_vec,
        instr_func_arr=instr_func_arr,
    )

    model_Skw *= 1 / np.max(model_Skw)

    return model_Skw


def spectral_density_model(wavelengths, settings, params):
    """
    Returns a `lmfit.Model` function for Thomson spectral density function


    Parameters
    ----------


    wavelengths : np.ndarray
        Wavelength array, in meters.


    settings : dict
        A dictionary of non-variable inputs to the spectral density function
        which must include the following:

            - probe_wavelength: Probe wavelength in meters
            - probe_vec : (3,) unit vector in the probe direction
            - scatter_vec: (3,) unit vector in the scattering direction
            - ion_species : list of Particle strings describing each ion species

        and may contain the following optional variables
            - electron_vdir : (e#, 3) array of electron velocity unit vectors
            - ion_vdir : (e#, 3) array of ion velocity unit vectors
            - instr_func : A function that takes a wavelength u.Quantity array
                        and returns a spectrometer insturment function as an
                        `numpy.ndarray`.

        These quantities cannot be varied during the fit.


    params : `lmfit.Parameters` object
        A Parameters object that must contains the following variables
            - n: 0th order density in m^-3
            - Te_e# : Temperature in eV
            - Ti_i# : Temperature in eV

        and may contain the following optional variables
            - efract_e# : Fraction of each electron population (must sum to 1) (optional)
            - ifract_i# : Fraction of each ion population (must sum to 1) (optional)
            - electron_speed_e# : Electron speed in m/s (optional)
            - ion_speed_i# : Ion speed in m/s (optional)

        where i# and e# are the number of electron and ion populations,
        zero-indexed, respectively (eg. 0,1,2...).

        These quantities can be either fixed or varying.


    Returns
    -------

    Spectral density (optimization function)


    Notes
    -----

    If an insturment function is included, the data should not include any
    `numpy.nan` values - instead regions with no data should be removed from
    both the data and wavelength arrays using `numpy.delete`.

    """

    # required settings
    req_settings = {
        "probe_wavelength",
        "probe_vec",
        "scatter_vec",
        "ion_species",
    }
    if req_settings - set(settings) != set():
        raise ValueError(
            f"Setting(s) {req_settings - set(settings)} was(were) not "
            "provided in kwarg 'settings', "
            f"but is(are) required."
        )

    # required parameters
    req_params = {"n"}
    if req_params - set(params) != set():
        raise ValueError(
            f"Parameter(s) {req_params - set(params)} was(were) not "
            " provided in kwarg 'params', "
            f"but is(are) required."
        )

    # **********************
    # Count number of populations
    # **********************
    if "efract_0" not in params:
        params.add("efract_0", value=1.0, vary=False)

    if "ifract_0" not in params:
        params.add("ifract_0", value=1.0, vary=False)

    num_e = _count_populations_in_params(params, "efract")
    num_i = _count_populations_in_params(params, "ifract")

    # **********************
    # Required settings and parameters per population
    # **********************
    for p, nums in zip(["Te", "Ti"], [num_e, num_i]):
        for num in range(nums):
            key = p + "_" + str(num)
            if key not in params:
                raise ValueError(
                    f"{p} was not provided in kwarg 'parameters', but is required."
                )

    # Create arrays of ion Z and mu from particles given
    # Create arrays of ion Z and mass from particles given
    ion_z = np.zeros(num_i)
    ion_mass = np.zeros(num_i)
    for i, species in enumerate(settings["ion_species"]):
        particle = Particle(species)
        ion_z[i] = particle.charge_number
        ion_mass[i] = particle_mass(particle).value
    settings["ion_z"] = ion_z
    settings["ion_mass"] = ion_mass

    # Automatically add an expression to the last efract parameter to
    # indicate that it depends on the others (so they sum to 1.0)
    # The resulting expression for the last of three will look like
    # efract_2.expr = "1.0 - efract_0 - efract_1"
    if num_e > 1:
        nums = ["1.0"] + [f"efract_{i}" for i in range(num_e - 1)]
        params[f"efract_{num_e - 1}"].expr = " - ".join(nums)

    if num_i > 1:
        nums = ["1.0"] + [f"ifract_{i}" for i in range(num_i - 1)]
        params[f"ifract_{num_i - 1}"].expr = " - ".join(nums)

    # **************
    # Electron velocity
    # **************
    electron_speed = np.zeros(num_e)
    for num in range(num_e):
        k = f"electron_speed_{num}"
        if k in params:
            electron_speed[num] = params[k].value
        else:
            # electron_speed[e] = 0 already
            params.add(k, value=0, vary=False)

    if "electron_vdir" not in settings:
        if np.all(electron_speed == 0):
            # vdir is arbitrary in this case because vel is zero
            settings["electron_vdir"] = np.ones([num_e, 3])
        else:
            raise ValueError(
                "Key 'electron_vdir' must be defined in kwarg 'settings' if "
                "any electron population has a non-zero speed (i.e. any "
                "params['electron_speed_<#>'] is non-zero)."
            )
    norm = np.linalg.norm(settings["electron_vdir"], axis=-1)
    settings["electron_vdir"] = settings["electron_vdir"] / norm[:, np.newaxis]

    # **************
    # Ion velocity
    # **************
    ion_speed = np.zeros(num_i)
    for num in range(num_i):
        k = f"ion_speed_{num}"
        if k in params:
            ion_speed[num] = params[k].value
        else:
            # ion_speed[i] = 0 already
            params.add(k, value=0, vary=False)

    if "ion_vdir" not in list(settings.keys()):
        if np.all(ion_speed == 0):
            # vdir is arbitrary in this case because vel is zero
            settings["ion_vdir"] = np.ones([num_i, 3])
        else:
            raise ValueError(
                "Key 'ion_vdir' must be defined in kwarg 'settings' if "
                "any ion population has a non-zero speed (i.e. any "
                "params['ion_speed_<#>'] is non-zero)."
            )
    norm = np.linalg.norm(settings["ion_vdir"], axis=-1)
    settings["ion_vdir"] = settings["ion_vdir"] / norm[:, np.newaxis]

    if "instr_func" not in settings or settings["instr_func"] is None:
        settings["instr_func_arr"] = None
    else:
        # Create instr_func array from instr_func
        instr_func = settings["instr_func"]
        wspan = (np.max(wavelengths) - np.min(wavelengths)) / 2
        eval_w = np.linspace(-wspan, wspan, num=wavelengths.size)
        instr_func_arr = instr_func(eval_w * u.m)

        if type(instr_func_arr) != np.ndarray:
            raise ValueError(
                "instr_func must be a function that returns a "
                "np.ndarray, but the provided function returns "
                f" a {type(instr_func_arr)}"
            )

        if wavelengths.shape != instr_func_arr.shape:
            raise ValueError(
                "The shape of the array returned from the "
                f"instr_func ({instr_func_arr.shape}) "
                "does not match the shape of the wavelengths "
                f"array ({wavelengths.shape})."
            )

        instr_func_arr *= 1 / np.sum(instr_func_arr)
        settings["instr_func_arr"] = instr_func_arr

        warnings.warn(
            "If an insturment function is included, the data "
            "should not include any `numpy.nan` values. "
            "Instead regions with no data should be removed from "
            "both the data and wavelength arrays using "
            " `numpy.delete`."
        )

    # TODO: raise an exception if the number of any of the ion or electron
    #       quantities isn't consistent with the number of that species defined
    #       by ifract or efract.

    # Create and return the lmfit.Model
    return Model(
        _spectral_density_model,
        independent_vars=["wavelengths"],
        nan_policy="omit",
        settings=settings,
    )
