import functools
import matplotlib.pyplot as plt
import numpy as np
import plasmaboundaries
import sympy

from astropy import constants
from astropy import units as u
from collections import namedtuple
from dataclasses import dataclass
from scipy import interpolate, optimize
from skimage import measure

grid_and_psi = namedtuple("GridAndPsi", ["R", "Z", "psi"])

from plasmapy.plasma.fluxsurface import FluxSurface


@dataclass
class SymbolicEquilibrium:
    aspect_ratio: float
    A: float
    elongation: float
    triangularity: float
    config: str
    B0: float

    def __post_init__(self):
        params = dict(
            aspect_ratio=self.aspect_ratio,
            A=self.A,
            elongation=self.elongation,
            triangularity=self.triangularity,
        )

        self.psi = plasmaboundaries.compute_psi(params, config=self.config)
        self.symbols = Rsym, Zsym = sympy.symbols("R Z")
        self.psisym = psisym = self.psi(Rsym, Zsym, pkg="sp")

        psifunc = sympy.lambdify([(Rsym, Zsym)], psisym, modules="numpy")
        minimization = optimize.minimize(psifunc, x0=[1.0, 0.0])
        R0, Z0 = minimization.x
        psi0 = minimization.fun
        Br = self.Br = -psisym.diff(Zsym) / Rsym
        Bz = self.Bz = psisym.diff(Rsym) / Rsym
        B = sympy.sqrt(Br ** 2 + Bz ** 2)
        mu0 = constants.mu0.si.value
        Bdiff_r = B.diff(Rsym)
        Bdiff_z = B.diff(Zsym)

        psym = (-(psi0 ** 2) / (mu0 * R0 ** 4) * (1 - self.A) * psisym).simplify()
        self.Bphi2 = (
            R0 ** 2
            / Rsym ** 2
            * (self.B0 ** 2 - 2 * psi0 ** 2 / R0 ** 4 * self.A * psisym)
        )
        self.Bphi = self.Bphi2 ** 0.5
        self.Bphifunc = sympy.lambdify((Rsym, Zsym), self.Bphi)
        self.Brfunc = sympy.lambdify((Rsym, Zsym), Br)
        self.Bzfunc = sympy.lambdify((Rsym, Zsym), Bz)
        self.Brdifffunc = sympy.lambdify((Rsym, Zsym), Bdiff_r)
        self.Bzdifffunc = sympy.lambdify((Rsym, Zsym), Bdiff_z)
        # assert (
        #     (Br * Rsym).diff(Rsym) / Rsym + Bz.diff(Zsym)
        # ).simplify() == 0  # due to toroidal symmetry
        # TODO change to close to 0 evaluated on grid

    # @functools.lru_cache # TODO get this to work somehow
    def get_grid_and_psi(self, rminmaxstep, zminmaxstep):
        rmin, rmax, rstep = rminmaxstep
        zmin, zmax, zstep = zminmaxstep

        r = np.arange(rmin, rmax, step=rstep)
        z = np.arange(zmin, zmax, step=zstep)
        R, Z = np.meshgrid(r, z)
        PSI = self.psi(R, Z)  # compute magnetic flux
        return grid_and_psi(R, Z, PSI)

    def plot(
        self,
        rminmaxstep=(0.6, 1.4, 0.01),
        zminmaxstep=(-0.6, 0.6, 0.01),
        savepath=None,
        vmax=0,
    ):
        R, Z, PSI = self.get_grid_and_psi(rminmaxstep, zminmaxstep)

        levels = np.sort(np.linspace(PSI.min(), 0, num=25))
        fig, ax = plt.subplots()
        CS = ax.contourf(R, Z, PSI, levels=levels, vmax=vmax)
        ax.contour(R, Z, PSI, levels=[0], colors="black")  # display the separatrix

        plt.colorbar(CS, label=r"Magnetic flux $\Psi$")
        ax.set_xlabel("Radius $R/R_0$")
        ax.set_ylabel("Height $z/R_0$")
        ax.set_aspect("equal")
        if savepath is not None:
            ax.savefig(savepath)
        return ax

    def get_flux_surface(
        self,
        psi_value,
        *,
        rminmaxstep=(0.6, 1.4, 0.01),
        zminmaxstep=(-0.6, 0.6, 0.01),
        RZPSI=None,
    ):
        if RZPSI is not None:
            R, Z, PSI = RZPSI
            rmax = R.max()
            rmin = R.min()
            zmax = Z.max()
            zmin = Z.min()
        else:
            rmin, rmax, rstep = rminmaxstep
            zmin, zmax, zstep = zminmaxstep
            R, Z, PSI = self.get_grid_and_psi(rminmaxstep, zminmaxstep)

        contours = measure.find_contours(PSI, psi_value, positive_orientation="high")
        if len(contours) == 0:
            raise ValueError(f"Could not find contour for psi = {psi_value}")
        elif len(contours) > 1:
            raise ValueError(
                f"Found multiple ({len(contours)})contours for psi = {psi_value}"
            )

        contour = contours[0]
        RcontourArrayUnits, ZcontourArrayUnits = contour[:, 1], contour[:, 0]

        Zcontour = ZcontourArrayUnits / PSI.shape[0] * (zmax - zmin) + zmin
        Rcontour = RcontourArrayUnits / PSI.shape[1] * (rmax - rmin) + rmin

        dZ = np.gradient(Zcontour)
        dR = np.gradient(Rcontour)
        dL = np.sqrt(dZ ** 2 + dR ** 2)

        Brvals = self.Brfunc(Rcontour, Zcontour)
        Bzvals = self.Bzfunc(Rcontour, Zcontour)
        Bprimervals = self.Brdifffunc(Rcontour, Zcontour)
        Bprimezvals = self.Bzdifffunc(Rcontour, Zcontour)
        Bphivals = self.Bphifunc(Rcontour, Zcontour)
        ρ = PSI / PSI.min()
        # TODO this might actually be wrong; check gradient in cylindrical
        ρprime_r = np.gradient(ρ, R[0], axis=1)
        ρprime_z = np.gradient(ρ, Z[:, 0], axis=0)

        ρprime2 = ρprime_z ** 2 + ρprime_r ** 2
        interpolator = interpolate.RectBivariateSpline(Z[:, 0], R[0], ρprime2)

        interpolated_GradRho2 = interpolator(Zcontour, Rcontour, grid=False)
        fs = FluxSurface(
            Rcontour,
            Zcontour,
            psi_value,
            Brvals,
            Bzvals,
            Bphivals,
            Bprimervals,
            Bprimezvals,
            interpolated_GradRho2,
        )
        return fs

    def get_multiple_flux_surfaces(
        self,
        psi_values,
        *,
        rminmaxstep=(0.6, 1.4, 0.01),
        zminmaxstep=(-0.6, 0.6, 0.01),
    ):
        rmin, rmax, rstep = rminmaxstep
        zmin, zmax, zstep = zminmaxstep
        R, Z, PSI = self.get_grid_and_psi(rminmaxstep, zminmaxstep)

        for psi in psi_values:
            yield self.get_flux_surface(
                psi, RZPSI=(R, Z, PSI),
            )


if __name__ == "__main__":
    params = plasmaboundaries.ITER
    eq = SymbolicEquilibrium(**params, config="non-null")
    eq.plot()
    fs = eq.get_flux_surface(0)
    fs.plot(B=True, n=True)
