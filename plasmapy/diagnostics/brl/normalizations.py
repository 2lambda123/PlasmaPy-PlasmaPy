"""Calculate the normalizations for the BRL theory."""
import astropy.units as u
import numpy as np

from plasmapy.utils.decorators import validate_quantities
from plasmapy.formulary.lengths import Debye_length


@validate_quantities(
    attracted_particle_temperature={
        "can_be_negative": False,
        "can_be_inf": False,
        "can_be_zero": False,
        "can_be_nan": False,
        "equivalencies": u.temperature_energy(),
    },
    repelled_particle_temperature={
        "can_be_negative": False,
        "can_be_inf": False,
        "can_be_zero": True,
        "can_be_nan": False,
        "equivalencies": u.temperature_energy(),
    },
    attracted_particle_charge_number={
        "can_be_inf": False,
        "can_be_zero": False,
        "can_be_nan": False,
    },
    repelled_particle_charge_number={
        "can_be_inf": False,
        "can_be_zero": False,
        "can_be_nan": False,
    },
)
def get_effective_attracted_to_repelled_temperature_ratio(
    attracted_particle_temperature: u.eV,
    repelled_particle_temperature: u.eV,
    attracted_particle_charge_number,
    repelled_particle_charge_number,
):
    r"""
    Calculate the effective temperature ratio of the attracted to repelled particle species.

    The effective temperature ratio is defined as

    .. math::
        \pi_6 = -\frac{T_+}{T_-} \frac{Z_-}{Z_+},

    where :math:`T_+` and :math:`T_-` are the temperatures of the attracted and 
    repelled particle species, and :math:`Z_+` and :math:`Z_-` are the signed 
    charge numbers of the attracted and repelled particle species.

    Parameters
    ----------
    attracted_particle_temperature, repelled_particle_temperature : `astropy.units.Quantity`
        The temperature of the attracted and repelled particle species.
    attracted_particle_charge_number, repelled_particle_charge_number : `float`
        The signed charge number of the attracted and repelled particle species (eg. positive for protons and negative for electrons).

    Returns
    -------
    effective_temperature_ratio : `float`
        The effective temperature ratio of the attracted to repelled particle species.

    Notes
    -----
    The effective temperature ratio is defined in equation (3.3) of the thesis.
    """
    effective_temperature_ratio = -(
        attracted_particle_temperature / repelled_particle_temperature
    ) * (repelled_particle_charge_number / attracted_particle_charge_number)
    return effective_temperature_ratio.to(u.dimensionless_unscaled).value


def get_normalized_potential(
    potential: u.V, attracted_particle_temperature: u.eV, attracted_particle_charge_number
):
    r"""
    Calculate the normalized potential.

    The normalized potential is defined as

    .. math::
        \chi_+ = Z_+ \frac{e \phi}{k T_+},

    where :math:`\phi` is the potential, :math:`T_+` is the temperature 
    of the attracted particle species, and :math:`e` is the elementary charge.

    Parameters
    ----------
    potential : `astropy.units.Quantity`
        The potential.
    attracted_particle_temperature : `astropy.units.Quantity`
        The temperature of the attracted particle species.
    attracted_particle_charge_number : `float`
        The signed charge number of the attracted particle species (eg. positive for protons and negative for electrons).

    Returns
    -------
    normalized_potential : `float`
        The normalized potential.

    Notes
    -----
    The normalized potential uses the same normalization as the probe potential,
    :math:`\chi_p_+`, in equation (3.2) of the thesis.
    """
    normalized_potential = attracted_particle_charge_number * (potential / attracted_particle_temperature).to(
        u.dimensionless_unscaled
    ).value
    return normalized_potential


def get_normalized_probe_radius(probe_radius: u.m, attracted_particle_temperature: u.eV, attracted_particle_density_at_infinity: u.m**-3, attracted_particle_charge_number):
    r"""
    Calculate the normalized probe radius.

    The normalized probe radius is defined as

    .. math::
        \pi_4 = \sqrt{\gamma_+} = \frac{R_p}{\lambda_D_+},

    where :math:`R_p` is the probe radius and :math:`\lambda_D_+` is the Debye length of the attracted species.

    Parameters
    ----------
    probe_radius : `astropy.units.Quantity`
        The probe radius.
    attracted_particle_temperature : `astropy.units.Quantity`
        The temperature of the attracted particle species.
    attracted_particle_density_at_infinity : `astropy.units.Quantity`
        The number density of the attracted species at infinity.
    attracted_particle_charge_number : `float`
        The signed charge number of the attracted particle species (eg. positive for protons and negative for electrons).

    Returns
    -------
    normalized_probe_radius : `float`
        The normalized probe radius.

    Notes
    -----
    The normalized probe radius is defined in equation (3.2) of the thesis.
    """
    debye_length = Debye_length(
        temperature=attracted_particle_temperature,
        number_density=attracted_particle_density_at_infinity,
    )
    normalized_probe_radius = np.abs(attracted_particle_charge_number) * (probe_radius / debye_length).to(u.dimensionless_unscaled).value
    return normalized_probe_radius

def renormalize_probe_radius_to_larger_debye_length(normalized_probe_radius, effective_attracted_to_repelled_temperature_ratio, charge_ratio=-1.0):
    r"""Renormalize the normalized probe radius to the larger Debye length.
    
    Since there are two species in the plasma, their Debye lengths may be 
    different. This function takes the probe radius normalized to the attracted 
    particles debye length and renormalizes it to the larger Debye length.

    Laframboise refers to the ``ratio of probe radius to larger debye length'', called 
    `ROGA`, yet the code in the thesis uses

    .. math::
    
       \texttt{ROGA} = \frac{R_p}{\lambda_D_+} \sqrt{\min\left(-\frac{T_+ Z_-}{T_- Z_+}, 1\right)}

    If we assume that :math:`-\frac{T_+ Z_-}{T_- Z_+} < 1` then

    .. math::

        \texttt{ROGA} &= \frac{R_p}{\lambda_D_+} \sqrt{-\frac{T_+ Z_-}{T_- Z_+}} \\
        &= R_p \sqrt{\frac{Z_+^2 e^2 N_{\inf +}}{\eps k T_+}} \sqrt{-\frac{T_+ Z_-}{T_- Z_+}} \\
        &= R_p \sqrt{\frac{-Z_+ Z_- e^2 N_{\inf +}}{\eps k T_-}}

    If we assume :math:`Z_+ = -Z_-` then the code actually uses the ``ratio of 
    probe radius to attracted particle debye length'' but if 
    :math:`Z_+ \neq -Z_-` then Laframboise is incorrect. Since Laframboise only 
    has solutions where :math:`Z_+ = -Z_-`, we'll assume that this is actually 
    an issue with the thesis code and correct for it in ours.

    Parameters
    ----------
    normalized_probe_radius : `float`
        The probe radius normalized to the attracted particle Debye length.
    effective_attracted_to_repelled_temperature_ratio : `float`
        The effective temperature ratio of the attracted to repelled particle 
        species as defined in `~plasmapy.diagnostics.brl.normalizations.get_effective_temperature_ratio`.
    charge_ratio : `float`, optional
        The ratio of the attracted particles signed charge to the repelled 
        particles signed charge, :math:`Z_+ / Z_-`. Default is `-1.0`.

    Returns
    -------
    renormalized_probe_radius : `float`
        The probe radius renormalized to the larger Debye length.
    """
    if charge_ratio >= 0:
        raise ValueError("The charge ratio must be negative.")

    return normalized_probe_radius * np.sqrt(
        min(effective_attracted_to_repelled_temperature_ratio / -charge_ratio, 1)
    )
