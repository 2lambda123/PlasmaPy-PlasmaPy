from __future__ import annotations

__all__ = [
    "FlowCalculator",
]


import functools
import numpy as np

from astropy import constants
from astropy import units as u
from collections import defaultdict, namedtuple

from .neoclassical import M_script, mu_hat, N_script, ξ

try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property

Fluxes = namedtuple("Fluxes", ["particle_flux", "heat_flux"])


def S_pt(ai, μ, fs, ne_grad, T_grad):
    pressure_gradient = constants.k_B * (ai.T_i * ne_grad + ai.number_density * T_grad)
    Spt = (
        fs.Fhat
        / ai.ion.charge
        / ai.number_density
        * u.Quantity(
            [
                pressure_gradient * μ[0, 0]
                + ai.number_density * constants.k_B * T_grad * μ[0, 1],
                pressure_gradient * μ[1, 0]
                + ai.number_density * constants.k_B * T_grad * μ[1, 1],
            ]
        )
    ).si
    Spt = np.append(Spt, 0)
    return Spt


class FlowCalculator:
    """
    This does, in fact, do most things for my thesis.
    """

    def __init__(
        self, all_species, flux_surface, density_gradient, temperature_gradient,
    ):
        self.all_species = all_species
        self.flux_surface = flux_surface
        self.density_gradient = defaultdict(lambda: 0 * u.m ** -4, **density_gradient)
        self.temperature_gradient = defaultdict(
            lambda: 0 * u.K / u.m, **temperature_gradient
        )

        self.S_pt = {}
        self.μ = {}
        self.Aai = {}
        self.thermodynamic_forces = {}
        self.pressure_gradient = {}

        for a in self.all_species:
            xi = ξ(a)
            for i, ai in enumerate(a):
                sym = ai.ionic_symbol
                if i == 0 or xi[i] == 0:
                    continue
                self.pressure_gradient[sym] = constants.k_B * (
                    ai.T_i * self.density_gradient[sym]
                    + ai.number_density * self.temperature_gradient[sym]
                )
                self.μ[sym] = mu_hat(i, a, self.all_species, self.flux_surface)
                self.S_pt[sym] = S_pt(
                    ai,
                    self.μ[ai.ionic_symbol],
                    self.flux_surface,
                    self.density_gradient[ai.ionic_symbol],
                    self.temperature_gradient[ai.ionic_symbol],
                )
                self.Aai[sym] = xi[i] * M_script(a, self.all_species) - self.μ[sym]
                # --- TD forces eq21
                Fhat = self.flux_surface.Fhat
                thermodynamic_forces = u.Quantity(
                    [
                        # Eq21
                        Fhat
                        / ai.ion.charge
                        / ai.number_density
                        * self.pressure_gradient[sym],
                        Fhat
                        / ai.ion.charge
                        * constants.k_B
                        * self.temperature_gradient[sym],
                    ]
                )

                thermodynamic_forces = np.append(
                    thermodynamic_forces, 0
                )  # because units
                self.thermodynamic_forces[sym] = thermodynamic_forces

    def rbar(self, a) -> u.Quantity:
        def gen():
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                Aai = self.Aai[sym]
                S_matrix = ξ(a)[i] * np.eye(3)
                rai_as_rows = np.linalg.solve(Aai, S_matrix)
                # TODO does not include r_pT, r_E, r_NBI yet. Should it?
                rbar_ingredient = ξ(a)[i] * rai_as_rows
                yield rbar_ingredient

        return sum(gen())

    @cached_property
    def rbar_sources(self) -> u.Quantity:
        results = []
        for a in self.all_species:

            def gen():
                for i, ai in enumerate(self.contributing_states(a)):
                    sym = ai.ionic_symbol
                    Aai = self.Aai[sym]
                    Spt = self.S_pt[sym]
                    rai_as_rows = np.linalg.solve(Aai, Spt)
                    # TODO use self.r_pt?
                    rbar_ingredient = ξ(a)[i] * rai_as_rows
                    yield rbar_ingredient

            results.append(sum(gen()))
        return np.concatenate(results).si

    def eq34matrix(self):
        output_matrix = u.Quantity(np.eye(3 * len(self.all_species)))

        for i, a in enumerate(self.all_species):
            rarray = self.rbar(a)
            for j, b in enumerate(self.all_species):
                narray = N_script(a, b).sum(axis=0, keepdims=True)
                result = narray * rarray.T
                output_matrix[3 * i : 3 * i + 3, 3 * j : 3 * j + 3] += result

        return output_matrix

    @cached_property
    def r_pt(self):
        results = {}
        for a in self.all_species:
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                Aai = self.Aai[sym]
                Spt = self.S_pt[sym]
                r_pt = np.linalg.solve(Aai, Spt).si
                results[sym] = r_pt
        return results

    @cached_property
    def Λ(self) -> dict:
        rhs = self.rbar_sources
        lhs = self.eq34matrix()
        ubar = np.linalg.solve(lhs, rhs)

        outputs = {}
        for a in self.all_species:
            # use Eq31 to get charge state flows from isotopic flows
            def gen():
                for j, b in enumerate(self.all_species):
                    ubar_b = ubar[3 * j : 3 * j + 3]
                    yield (N_script(a, b) * ubar_b.reshape(1, -1)).sum(axis=1)

            outputs[a.base_particle] = -sum(gen())
        return outputs

    @cached_property
    def flows(self) -> dict:
        outputs = {}
        for a in self.all_species:
            Λ = self.Λ[a.base_particle]
            xi = ξ(a)
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                Aai = self.Aai[sym]
                S_ai = xi[i] * np.diag(Λ)
                rai_as_rows = np.linalg.solve(Aai, S_ai)
                order_flow_sum = (
                    (Λ.reshape(-1, 1) * rai_as_rows).sum(axis=0).si.value
                )  # TODO fix units

                r_pt = self.r_pt[sym]
                flows = order_flow_sum + r_pt.value  # Eq31
                outputs[ai.ionic_symbol] = flows * u.V / u.m  # TODO fix units
        return outputs

    @staticmethod
    def contributing_states(a):
        xi = ξ(a)
        for i, ai in enumerate(a):
            if xi[i] == 0:
                continue
            yield ai

    def funnymatrix(self, a_symbol):
        a = self.all_species[a_symbol]  # TODO workaround while they're unhashable
        M = M_script(a, self.all_species)
        outputs = {}
        for ai in self.contributing_states(a):
            sym = ai.ionic_symbol
            S = self.S_pt[sym]
            output = S * M
            for b in self.all_species:
                N = N_script(a, b)
                xi = ξ(b)
                for j, bj in enumerate(self.contributing_states(b)):
                    output += xi[j] * N * self.S_pt[bj.ionic_symbol]
            outputs[sym] = output
        return outputs

    @cached_property
    def _fluxes_BP(self):
        Fhat = self.flux_surface.Fhat
        fs = self.flux_surface
        B2fsav = fs.flux_surface_average(fs.B2) * u.T ** 2  # flux surface averaged B^2
        results = {}
        for a in self.all_species:
            for (
                ai
            ) in (
                a
            ):  # this could be rfactored out by iterating over self.flows, instead, given a way to access ionizationstate back from ioniclevel
                sym = ai.ionic_symbol
                if sym not in self.flows:
                    continue
                u_velocity = self.flows[sym]

                u_θ = (u_velocity + self.thermodynamic_forces[sym]) / B2fsav
                μ = self.μ[sym]
                Γ_BP = -(Fhat / ai.ion.charge * (μ[0, :] * u_θ).sum()).si
                # TODO verify unit; does not look right
                q_BP = -(
                    fs.Fhat
                    * constants.k_B
                    * ai.T_i
                    / ai.ion.charge
                    * (μ[1, :] * u_θ).sum()
                ).si
                results[sym] = Fluxes(Γ_BP.si, q_BP.si)
        return results

    @cached_property
    def _fluxes_PS(self):
        fs = self.flux_surface
        B2fsav = fs.flux_surface_average(fs.B2) * u.T ** 2  # flux surface averaged B^2
        Binv2fsav = fs.flux_surface_average(1 / fs.B2) / u.T ** 2
        results = {}
        fs = self.flux_surface
        for a in self.all_species:
            xi = ξ(a)
            silly = self.funnymatrix(a.base_particle)
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                prefactor = (
                    -fs.Fhat / ai.ion.charge * xi[i] / B2fsav * (1 - B2fsav * Binv2fsav)
                )
                Γ_PS = prefactor * silly[sym][0].sum()
                q_PS = prefactor * constants.k_B * ai.T_i * silly[sym][1].sum()
                results[sym] = Fluxes(Γ_PS.si, q_PS.si)
        return results

    @cached_property
    def _fluxes_CL(self):
        # breakpoint()
        fs = self.flux_surface
        FSA = fs.flux_surface_average(fs.GradRho2 / fs.B2) / u.T ** 2 / u.m
        # TODO if FSA does not drop units, the above line is completely wrong
        Fhat = self.flux_surface.Fhat
        results = {}
        for a in self.all_species:
            xi = ξ(a)
            silly = self.funnymatrix(a.base_particle)
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                prefactor = 1 / Fhat * xi[i] / ai.ion.charge * FSA
                Γ_CL = prefactor * silly[sym][0].sum()
                q_CL = prefactor * constants.k_B * ai.T_i * silly[sym][1].sum()
                results[sym] = Fluxes(Γ_CL.si, q_CL.si)
        return results

    @cached_property
    def fluxes(self):
        results = {}
        for a in self.all_species:
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                Γ_BP, q_BP = self._fluxes_BP[sym]
                Γ_PS, q_PS = self._fluxes_PS[sym]
                Γ_CL, q_CL = self._fluxes_CL[sym]
                results[sym] = Fluxes(Γ_BP + Γ_PS + Γ_CL, q_BP + q_PS + q_CL)
        return results

    @cached_property
    def diffusion_coefficient(self):
        results = {}
        for a in self.all_species:
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                flux = self.fluxes[ai].particle_flux
                results[sym] = (
                    -flux / self.density_gradient[sym]
                )  # Eq48 TODO this is a partial adaptation
        return results

    @cached_property
    def thermal_conductivity(self):
        results = {}
        for a in self.all_species:
            for i, ai in enumerate(self.contributing_states(a)):
                sym = ai.ionic_symbol
                flux = self.fluxes[ai].heat_flux
                results[sym] = -flux / self.temperature_gradient[sym]
        return results

    @cached_property
    def bootstrap_current(self):
        def gen():
            for a in self.all_species:
                for i, ai in enumerate(self.contributing_states(a)):
                    sym = ai.ionic_symbol
                    yield ai.ion.charge * ai.number_density * self.r_pt[sym][
                        0
                    ]  # eq 37, second term

        return sum(gen())
