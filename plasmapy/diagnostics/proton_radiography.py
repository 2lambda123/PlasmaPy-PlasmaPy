"""
Routines for the analysis of proton radiographs. These routines can be broadly
classified as either creating synthetic radiographs from prescribed fields or
methods of 'inverting' experimentally created radiographs to reconstruct the
original fields (under some set of assumptions).
"""

__all__ = [
    "SyntheticProtonRadiograph",
]

import astropy.constants as const
import astropy.units as u
import numpy as np
import sys
import warnings

from tqdm import tqdm

from plasmapy.plasma.grids import AbstractGrid
from plasmapy.simulation.particle_integrators import boris_push


def _rot_a_to_b(a, b):
    r"""
    Calculates the 3D rotation matrix that will rotate vector a to be aligned
    with vector b.
    """
    # Normalize both vectors
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)

    # Manually handle the case where a and b point in opposite directions
    if np.dot(a, b) == -1:
        return -np.identity(3)

    axb = np.cross(a, b)
    c = np.dot(a, b)
    vskew = np.array(
        [[0, -axb[2], axb[1]], [axb[2], 0, -axb[0]], [-axb[1], axb[0], 0]]
    ).T  # Transpose to get right orientation

    return np.identity(3) + vskew + np.dot(vskew, vskew) / (1 + c)


def _coerce_to_cartesian_si(pos):
    """
    Takes a tuple of `astropy.unit.Quantity` values representing a position
    in space in either Cartesian, cylindrical, or spherical coordinates, and
    returns a numpy array representing the same point in Cartesian
    coordinates and units of meters.
    """
    # Auto-detect geometry based on units
    geo_units = [x.unit for x in pos]
    if geo_units[2].is_equivalent(u.rad):
        geometry = "spherical"
    elif geo_units[1].is_equivalent(u.rad):
        geometry = "cylindrical"
    else:
        geometry = "cartesian"

    # Convert geometrical inputs between coordinates systems
    pos_out = np.zeros(3)
    if geometry == "cartesian":
        x, y, z = pos
        pos_out[0] = x.to(u.m).value
        pos_out[1] = y.to(u.m).value
        pos_out[2] = z.to(u.m).value

    elif geometry == "cylindrical":
        r, t, z = pos
        r = r.to(u.m)
        t = t.to(u.rad).value
        z = z.to(u.m)
        pos_out[0] = (r * np.cos(t)).to(u.m).value
        pos_out[1] = (r * np.sin(t)).to(u.m).value
        pos_out[2] = z.to(u.m).value

    elif geometry == "spherical":
        r, t, p = pos
        r = r.to(u.m)
        t = t.to(u.rad).value
        p = p.to(u.rad).value

        pos_out[0] = (r * np.sin(t) * np.cos(p)).to(u.m).value
        pos_out[1] = (r * np.sin(t) * np.sin(p)).to(u.m).value
        pos_out[2] = (r * np.cos(t)).to(u.m).value

    return pos_out


class SyntheticProtonRadiograph:
    r"""
    Represents a proton radiography experiment with simulated or
    calculated E and B fields given at positions defined by a grid of spatial
    coordinates. The proton source and detector plane are defined by vectors
    from the origin of the grid.

    Parameters
    ----------
    grid : `~plasmapy.plasma.grids.AbstractGrid` or subclass thereof
        A Grid object containing the required quantities [E_x, E_y, E_z, B_x, B_y, B_z].
        If any of these quantities are missing, a warning will be given and that
        quantity will be assumed to be zero everywhere.

    source : `~astropy.units.Quantity`, shape (3)
        A vector pointing from the origin of the grid to the location
        of the proton point source. This vector will be interpreted as
        being in either cartesian, cylindrical, or spherical coordinates
        based on its units. Valid geometries are:
        * Cartesian (x,y,z) : (meters, meters, meters)
        * cylindrical (r, theta, z) : (meters, radians, meters)
        * spherical (r, theta, phi) : (meters, radians, radians)
        In spherical coordinates theta is the polar angle.

    detector : `~astropy.units.Quantity`, shape (3)
        A vector pointing from the origin of the grid to the center
        of the detector plane. The vector from the source point to this
        point defines the normal vector of the detector plane. This vector
        can also be specified in cartesian, cylindrical, or spherical
        coordinates (see the `source` keyword).

    detector_hdir : `numpy.ndarray`, shape (3), optional
        A unit vector (in Cartesian coordinates) defining the horizontal
        direction on the detector plane. By default, the horizontal axis in the
        detector plane is defined to be perpendicular to both the
        source-to-detector vector and the z-axis (unless the source-to-detector axis
        is parallel to the z axis, in which case the horizontal axis is the x-axis).

        The detector vertical axis is then defined
        to be orthgonal to both the source-to-detector vector and the
        detector horizontal axis.

    verbose : bool, optional
        If true, updates on the status of the program will be printed
        into the command line while running.
    """

    def __init__(
        self,
        grid: AbstractGrid,
        source: u.m,
        detector: u.m,
        detector_hdir=None,
        verbose=True,
    ):

        # self.grid is the grid object
        self.grid = grid
        # self.grid_arr is the grid positions in si units. This is created here
        # so that it isn't continously called later
        self.grid_arr = grid.grid.to(u.m).value

        self.verbose = verbose

        # ************************************************************************
        # Setup the source and detector geometries
        # ************************************************************************

        self.source = _coerce_to_cartesian_si(source)
        self.detector = _coerce_to_cartesian_si(detector)
        self._log(f"Source: {self.source} m")
        self._log(f"Detector: {self.detector} m")

        # Calculate normal vectors (facing towards the grid origin) for both
        # the source and detector planes
        self.src_n = -self.source / np.linalg.norm(self.source)
        self.det_n = -self.detector / np.linalg.norm(self.detector)

        # Vector directly from source to detector
        self.src_det = self.detector - self.source

        # Magnification
        self.mag = 1 + np.linalg.norm(self.detector) / np.linalg.norm(self.source)
        self._log(f"Magnification: {self.mag}")

        # Check that source-detector vector actually passes through the grid
        if not self.grid.vector_intersects(self.source * u.m, self.detector * u.m):
            raise ValueError(
                "The vector between the source and the detector "
                "does not intersect the grid provided!"
            )

        # ************************************************************************
        # Define the detector plane
        # ************************************************************************

        # Load or calculate the detector hdir
        if detector_hdir is not None:
            self.det_hdir = detector_hdir / np.linalg.norm(detector_hdir)
        else:
            self.det_hdir = self._default_detector_hdir()

        # Calculate the detector vdir
        ny = np.cross(self.det_hdir, self.det_n)
        self.det_vdir = -ny / np.linalg.norm(ny)

        # ************************************************************************
        # Validate the E and B fields
        # ************************************************************************

        req_quantities = ["E_x", "E_y", "E_z", "B_x", "B_y", "B_z"]
        for rq in req_quantities:

            # Error check that grid contains E and B variables required
            if rq not in self.grid.quantities:
                warnings.warn(
                    f"{rq} not specified for provided grid."
                    "This quantity will be assumed to be zero.",
                    RuntimeWarning,
                )
                # If missing, warn user and then replace with an array of zeros
                unit = self.grid._recognized_quantities[rq].unit
                arg = {rq: np.zeros(self.grid.shape) * unit}
                self.grid.add_quantities(**arg)

            # Check that there are no infinite values
            if not np.isfinite(self.grid[rq]).all():
                raise ValueError(
                    f"Input arrays must be finite: {rq} contains "
                    "either NaN or infinite values."
                )

            # Check that the max values on the edges of the arrays are
            # small relative to the maximum values on that grid
            arr = np.abs(self.grid[rq])
            edge_max = np.max(
                np.array(
                    [
                        np.max(arr[0, :, :]),
                        np.max(arr[-1, :, :]),
                        np.max(arr[:, 0, :]),
                        np.max(arr[:, -1, :]),
                        np.max(arr[:, :, 0]),
                        np.max(arr[:, :, -1]),
                    ]
                )
            )

            if edge_max > 1e-3 * np.max(arr):
                unit = grid.recognized_quantities[rq].unit
                warnings.warn(
                    "Fields should go to zero at edges of grid to avoid "
                    f"non-physical effects, but a value of {edge_max:.2E} {unit} was "
                    f"found on the edge of the {rq} array. Consider applying a "
                    "envelope function to force the fields at the edge to go to "
                    "zero.",
                    RuntimeWarning,
                )

    def _default_detector_hdir(self):
        """
        Calculates the default horizontal unit vector for the detector plane
        (see __init__ description for details)
        """
        # Create unit vectors that define the detector plane
        # Define plane  horizontal axis
        if np.allclose(np.abs(self.det_n), np.array([0, 0, 1])):
            nx = np.array([1, 0, 0])
        else:
            nx = np.cross(np.array([0, 0, 1]), self.det_n)
        nx = nx / np.linalg.norm(nx)
        return nx

    def _log(self, msg):
        if self.verbose:
            print(msg)

    # Define some constants so they don't get constantly re-evaluated
    _e = const.e.si.value
    _c = const.c.si.value
    _m_p = const.m_p.si.value

    # *************************************************************************
    # Particle creation methods
    # *************************************************************************

    def _angles_monte_carlo(self):
        """
        Generates angles for each particle randomly such that the flux
        per solid angle is uniform
        """
        # Create a probability vector for the theta distribution
        # Theta must follow a sine distribution in order for the proton
        # flux per solid angle to be uniform.
        arg = np.linspace(0, self.max_theta, num=int(1e5))
        prob = np.sin(arg)
        prob *= 1 / np.sum(prob)

        # Randomly choose theta's weighted with the sine probabilities
        theta = np.random.choice(arg, size=self.nparticles, replace=True, p=prob)

        # Also generate a uniform phi distribution
        phi = np.random.uniform(size=self.nparticles) * 2 * np.pi

        return theta, phi

    def _angles_uniform(self):
        """
        Generates angles for each particle such that their velocities are
        uniformly distributed on a grid in theta and phi.
        """
        # Calculate the approximate square root
        n_per = np.floor(np.sqrt(self.nparticles)).astype(np.int32)

        # Set new nparticles to be a perfect square
        self.nparticles = n_per ** 2

        # Create an imaginary grid positioned 1 unit from the source
        # and spanning max_theta at the corners
        extent = np.sin(self.max_theta) / np.sqrt(2)
        arr = np.linspace(-extent, extent, num=n_per)
        harr, varr = np.meshgrid(arr, arr, indexing="ij")

        # calculate the angles from the source for each point in
        # the grid.
        theta = np.arctan(np.sqrt(harr ** 2 + varr ** 2))
        phi = np.arctan2(varr, harr)

        return theta.flatten(), phi.flatten()

    def create_particles(
        self,
        nparticles,
        proton_energy,
        max_theta=0.9 * np.pi / 2 * u.rad,
        charge=None,
        mass=None,
        distribution="monte-carlo",
    ):
        r"""
        Generates the angular distributions about the Z-axis, then
        rotates those distributions to align with the source-to-detector axis.

        By default, protons are generated over almost the entire pi/2. However,
        if the detector is far from the source, many of these particles will
        never be observed. The max_theta keyword allows these extraneous
        particles to be neglected to focus computational resources on the
        particles who will actually hit the detector.

        nparticles : integer
            The number of particles to include in the simulation. The default
            is 1e5.

        proton_energy : `~astropy.units.Quantity`
            The energy of the particle, in units convertible to eV

        max_theta : `~astropy.units.Quantity`, optional
            The largest velocity vector angle (measured from the
            source-to-detector axis) for which particles should be generated.
            Decreasing this angle can eliminate particles that would never
            reach the detector region of interest. The default is 0.9*pi/2.
            Units must be convertable to radians.

        charge : `~astropy.units.Quantity`
            The charge of the particle, in units convertable to Columbs.
            The default is the proton charge.


        mass : `~astropy.units.Quantity`
            The mass of the particle, in units convertable to kg.
            The default is the proton mass.


        distribution: str
            A keyword which determines how particles will be distributed
            in velocity space. Options are:

                - 'monte-carlo': velocities will be chosen randomly,
                    such that the flux per solid angle is uniform.

                - 'uniform': velocities will be distrbuted such that,
                   left unpreturbed,they will form a uniform pattern
                   on the detection plane.

            Simulations run in the `uniform` mode will imprint a grid pattern
            on the image, but will well-sample the field grid with a
            smaller number of particles. The default is `monte-carlo`


        """
        self._log("Creating Particles")

        # Load inputs
        self.nparticles = int(nparticles)
        self.proton_energy = proton_energy.to(u.eV).value
        self.max_theta = max_theta.to(u.rad).value
        if charge is None:
            charge = self._e
        if mass is None:
            mass = self._m_p
        self.q = charge
        self.m = mass

        # Calculate the velocity corresponding to the proton energy
        ER = self.proton_energy * 1.6e-19 / (self.m * self._c ** 2)
        self.v0 = self._c * np.sqrt(1 - 1 / (ER + 1) ** 2)

        if distribution == "monte-carlo":
            theta, phi = self._angles_monte_carlo()
        elif distribution == "uniform":
            theta, phi = self._angles_uniform()

        # Store the theta's to later compare with max_grid_theta
        # to determine which particles will never cross the grid
        self.theta0 = theta

        # Construct the velocity distribution around the z-axis
        self.v = np.zeros([self.nparticles, 3])
        self.v[:, 0] = self.v0 * np.sin(theta) * np.cos(phi)
        self.v[:, 1] = self.v0 * np.sin(theta) * np.sin(phi)
        self.v[:, 2] = self.v0 * np.cos(theta)

        # Calculate the rotation matrix that rotates the z-axis
        # onto the source-detector axis
        a = np.array([0, 0, 1])
        b = self.detector - self.source
        rot = _rot_a_to_b(a, b)

        # Apply rotation matrix to calculated velocity distribution
        self.v = np.matmul(self.v, rot)

        # Place particles at the source
        self.x = np.outer(np.ones(self.nparticles), self.source)

    # *************************************************************************
    # Run/push loop methods
    # *************************************************************************

    def _max_theta_grid(self):
        r"""
        Using the grid and the source position, compute the maximum particle
        theta that will impact the grid. This value can be used to determine
        which particles are worth tracking.
        """
        ind = 0
        theta = np.zeros([8])
        for x in [0, -1]:
            for y in [0, -1]:
                for z in [0, -1]:
                    # Souce to grid corner vector
                    vec = self.grid_arr[x, y, z, :] - self.source

                    # Calculate angle between vec and the source-to-detector
                    # axis, which is the central axis of the proton beam
                    theta[ind] = np.arccos(
                        np.dot(vec, self.src_det)
                        / np.linalg.norm(vec)
                        / np.linalg.norm(self.src_det)
                    )
                    ind += 1
        return np.max(theta)

    def _adaptive_dt(self, Ex, Ey, Ez, Bx, By, Bz):
        r"""
        Calculate the appropraite dt based on a number of considerations
        including the local grid resolution (ds) and the gyroperiod of the
        particles in the current fields.
        """
        # If dt was explicitly set, skip the rest of this function
        if self.dt.size == 1:
            return self.dt

        # Compute the timestep indicated by the grid resolution
        ds = self.grid.grid_resolution.to(u.m).value
        gridstep = 0.5 * (np.min(ds) / self.v0)

        # If not, compute a number of possible timesteps
        # Compute the cyclotron gyroperiod
        Bmag = np.max(np.sqrt(Bx ** 2 + By ** 2 + Bz ** 2)).to(u.T).value

        # Compute the gyroperiod
        if Bmag == 0:
            gyroperiod = np.inf
        else:
            gyroperiod = 2 * np.pi * self._m_p / (self._e * np.max(Bmag))

        # TODO: introduce a minimum timestep based on electric fields too!

        # Create an array of all the possible time steps we computed
        candidates = np.array([gyroperiod, gridstep])

        # Enforce limits on dt
        candidates = np.clip(candidates, self.dt[0], self.dt[1])

        # dt is the min of the remaining candidates
        return np.min(candidates)

    def _advance_to_grid(self):
        r"""
        Advances all particles to the timestep when the first particle should
        be entering the grid. Doing in this in one step (rather than pushing
        the particles through zero fields) saves computation time.
        """
        # Distance from the source to the nearest gridpoint
        dist = np.min(np.linalg.norm(self.grid_arr - self.source, axis=3))

        # Find the particle with the highest speed towards the grid
        vmax = np.max(np.dot(self.v, self.src_n))

        # Time for fastest possible particle to reach the grid.
        t = dist / vmax

        # Coast the particles to the advanced position
        self.x = self.x + self.v * t

    def _generate_null(self):
        r"""
        Calculate the distribution of particles on the detector plane in the absence
        of any simulated fields.

        These positions are used to quickly compute null radiographs, which are
        used to determine the degree of deflection.
        """
        # Calculate the unit vector from the source to the detector
        dist = np.linalg.norm(self.source_to_detector)
        uvec = self.source_to_detector / dist

        # Calculate the remaining distance each particle needs to travel
        # along that unit vector
        remaining = np.dot(self.source, uvec)

        # Calculate the time remaining to reach that plane and push
        t = (dist - remaining) / np.dot(self.v, uvec)

        # Calculate the particle positions for that case
        self.x0 = self.source + self.v * np.outer(t, np.ones(3))

    def _advance_to_detector(self):
        r"""
        Advances all particles to the detector plane. This method will be
        called after all particles have cleared the grid.

        This step applies to all particles, including those that never touched
        the grid.
        """
        dist_remaining = np.dot(self.x, self.det_n) + np.linalg.norm(self.detector)

        v_towards_det = np.dot(self.v, -self.det_n)

        # Time remaining for each particle to reach detector plane
        t = dist_remaining / v_towards_det

        # If particles have not yet reached the detector plane and are moving
        # away from it, they will never reach the detector.
        # So, we can remove them from the arrays
        condition = np.logical_and(v_towards_det < 0, dist_remaining > 0)
        ind = np.nonzero(np.where(condition, 0, 1))[0]
        self.x = self.x[ind, :]
        self.v = self.v[ind, :]
        self.nparticles_grid = self.x.shape[0]
        t = t[ind]

        self.x += self.v * np.outer(t, np.ones(3))

        # Check that all points are now in the detector plane
        # (Eq. of a plane is nhat*x + d = 0)
        plane_eq = np.dot(self.x, self.det_n) + np.linalg.norm(self.detector)
        assert np.allclose(plane_eq, np.zeros(self.nparticles_grid), atol=1e-6)

    def _push(self):
        r"""
        Advance particles using an implementation of the time-centered
        Boris algorithm
        """
        # Get a list of positions (input for interpolator)
        pos = self.x[self.grid_ind, :] * u.m

        # Update the list of particles on and off the grid
        self.on_grid = self.grid.on_grid(pos)
        # entered_grid is zero at the end if a particle has never
        # entered the grid
        self.entered_grid += self.on_grid

        # Estimate the E and B fields for each particle
        # Note that this interpolation step is BY FAR the slowest part of the push
        # loop. Any speed improvements will have to come from here.
        if self.field_weighting == "volume averaged":
            Ex, Ey, Ez, Bx, By, Bz = self.grid.volume_averaged_interpolator(
                pos, "E_x", "E_y", "E_z", "B_x", "B_y", "B_z", persistent=True,
            )
        elif self.field_weighting == "nearest neighbor":
            Ex, Ey, Ez, Bx, By, Bz = self.grid.nearest_neighbor_interpolator(
                pos, "E_x", "E_y", "E_z", "B_x", "B_y", "B_z", persistent=True,
            )

        # Create arrays of E and B as required by push algorithm
        E = np.array(
            [Ex.to(u.V / u.m).value, Ey.to(u.V / u.m).value, Ez.to(u.V / u.m).value]
        )
        E = np.moveaxis(E, 0, -1)
        B = np.array([Bx.to(u.T).value, By.to(u.T).value, Bz.to(u.T).value])
        B = np.moveaxis(B, 0, -1)

        # Calculate the adaptive timestep from the fields currently experienced
        # by the particles
        # If user sets dt explicitly, that's handled in _adpative_dt
        dt = self._adaptive_dt(Ex, Ey, Ez, Bx, By, Bz)

        # TODO: Test v/c and implement relativistic Boris push when required
        # vc = np.max(v)/_c

        x = self.x[self.grid_ind, :]
        v = self.v[self.grid_ind, :]
        boris_push(x, v, B, E, self.q, self.m, dt)
        self.x[self.grid_ind, :] = x
        self.v[self.grid_ind, :] = v

    def _stop_condition(self):
        r"""
        The stop condition is that most of the particles have entered the grid
        and almost all have now left it.
        """
        # Count the number of particles who have entered, which is the
        # number of non-zero entries in entered_grid
        n_entered = np.nonzero(self.entered_grid)[0].size

        # How many of the particles have entered the grid
        entered = np.sum(n_entered) / self.nparticles_grid

        # Of the particles that have entered the grid, how many are currently
        # on the grid?
        # if/else avoids dividing by zero
        if np.sum(n_entered) > 0:
            still_on = np.sum(self.on_grid) / np.sum(n_entered)
        else:
            still_on = 0.0

        if entered > 0.1 and still_on < 0.001:
            # Warn user if < 10% of the particles ended up on the grid
            if n_entered < 0.1 * self.nparticles:
                warnings.warn(
                    f"Only {100*n_entered/self.nparticles:.2f}% of "
                    "particles entered the field grid: consider "
                    "decreasing the max_theta to increase this "
                    "number.",
                    RuntimeWarning,
                )

            return True
        else:
            return False

    def run(
        self, dt=None, field_weighting="volume averaged",
    ):
        r"""
        Runs a particle-tracing simulation.
        Timesteps are adaptively calculated based on the
        local grid resolution of the particles and the electric and magnetic
        fields they are experiencing. After all particles
        have left the grid, they are advanced to the
        detector plane where they can be used to construct a synthetic
        diagnostic image.

        Parameters
        ----------

        dt : `~astropy.units.Quantity`, optional
            An explicitly set timestep in units convertable to seconds.
            Setting this optional keyword overrules the adaptive time step
            capability and forces the use of this timestep throughout. If a tuple
            of timesteps is provided, the adaptive timstep will be clamped
            between the first and second values.

        field_weighting : str
            String that selects the field weighting algorithm used to determine
            what fields are felt by the particles. Options are:

            * 'nearest neighbor': Particles are assigned the fields on
                the grid vertex closest to them.

            * 'volume averaged' : The fields experienced by a particle are a
                volume-average of the eight grid points surrounding them.

            The default is 'volume averaged'.

        Returns
        -------
        None.

        """

        # Load and validate inputs
        field_weightings = ["volume averaged", "nearest neighbor"]
        if field_weighting in field_weightings:
            self.field_weighting = field_weighting
        else:
            raise ValueError(
                f"{field_weighting} is not a valid option for ",
                "field_weighting. Valid choices are",
                f"{field_weightings}",
            )

        if dt is None:
            # Set dt as an infinite range by default (auto dt with no restrictions)
            self.dt = np.array([0.0, np.inf]) * u.s
        else:
            self.dt = dt
        self.dt = (self.dt).to(u.s).value

        # Check to make sure particles have already been generated
        if not hasattr(self, "x"):
            raise ValueError(
                "The create_particles method must be called before "
                "running the particle tracing algorithm."
            )

        # Determine the angle above which particles will not hit the grid
        # these particles can be ignored until the end of the simulation,
        # then immediately advanced to the detector grid with their original
        # velocities
        max_theta_grid = self._max_theta_grid()

        # This array holds the indices of all particles that WILL hit the grid
        # Only these particles will actually be pushed through the fields
        self.grid_ind = np.where(self.theta0 < max_theta_grid)[0]
        self.nparticles_grid = len(self.grid_ind)

        # Create flags for tracking when particles during the simulation
        # on_grid -> zero if the particle is off grid, 1
        self.on_grid = np.zeros([self.nparticles_grid])
        # Entered grid -> non-zero if particle EVER entered the grid
        self.entered_grid = np.zeros([self.nparticles_grid])

        # Advance the particles to the near the start of the grid
        self._advance_to_grid()

        # Initialize a "progress bar" (really more of a meter)
        # Setting sys.stdout lets this play nicely with regular print()
        pbar = tqdm(
            initial=0,
            total=self.nparticles_grid + 1,
            disable=not self.verbose,
            desc="Particles on grid",
            unit="particles",
            bar_format="{l_bar}{bar}{n:.1e}/{total:.1e} {unit}",
            file=sys.stdout,
        )

        # Push the particles until the stop condition is satisfied
        # (no more particles on the simulation grid)
        while not self._stop_condition():
            n_on_grid = np.sum(self.on_grid)
            pbar.n = n_on_grid
            pbar.last_print_n = n_on_grid
            pbar.update()

            self._push()
        pbar.close()

        # Advance the particles to the image plane
        # At this stage, remove any particles that will never hit the detector plane
        self._advance_to_detector()

        self._log("Run completed")

    # *************************************************************************
    # Synthetic diagnostic methods (creating output)
    # *************************************************************************

    def synthetic_radiograph(
        self, size=None, bins=[200, 200], null=False, optical_density=False
    ):
        r"""
        Calculate a "synthetic radiograph" (particle count histogram in the
        image plane).

        Parameters
        ----------
        size : `~astropy.units.Quantity`, shape (2,2)
            The size of the detector array, specified as the minimum
            and maximum values included in both the horizontal and vertical
            directions in the detector plane coordinates. Shape is
            [[hmin,hmax], [vmin, vmax]]. Units must be convertable to meters.

        bins : array of integers, shape (2)
            The number of bins in each direction in the format [hbins, vbins].
            The default is [200,200].

        null: bool
            If True, returns the intensity in the image plane in the absence
            of simulated fields.

        optical_density: bool
            If True, return the optical density rather than the intensity

            .. math::
                OD = -log_{10}(Intensity/I_0)

            where I_O is the intensity on the detector plane in the absence of
            simulated fields. Default is False.

        Returns
        -------
        hax : `~astropy.units.Quantity` array shape (hbins,)
            The horizontal axis of the synthetic radiograph in meters.

        vax : `~astropy.units.Quantity` array shape (vbins, )
            The vertical axis of the synthetic radiograph in meters.

        intensity : ndarray, shape (hbins, vbins)
            The number of protons counted in each bin of the histogram.
        """

        # Note that, at the end of the simulation, all particles were moved
        # into the image plane.

        # If null is True, use the predicted positions in the absence of
        # simulated fields
        if null:
            x = self.x0
        else:
            x = self.x

        # Determine locations of points in the detector plane using unit
        # vectors
        xloc = np.dot(x - self.detector, self.det_hdir)
        yloc = np.dot(x - self.detector, self.det_vdir)

        if size is None:
            # If a detector size is not given, choose lengths based on the
            # dimensions of the grid
            w = self.mag * np.max(
                [
                    np.max(np.abs(self.grid.pts0.to(u.m).value)),
                    np.max(np.abs(self.grid.pts1.to(u.m).value)),
                    np.max(np.abs(self.grid.pts2.to(u.m).value)),
                ]
            )

            size = np.array([[-w, w], [-w, w]]) * self.grid.unit

        # Generate the histogram
        intensity, h, v = np.histogram2d(
            xloc, yloc, range=size.to(u.m).value, bins=bins
        )

        # h, v are the bin edges: compute the centers to produce arrays
        # of the right length (then trim off the extra point)
        h = ((h + np.roll(h, -1)) / 2)[0:-1]
        v = ((v + np.roll(v, -1)) / 2)[0:-1]

        # Throw a warning if < 50% of the particles are included on the
        # histogram
        percentage = 100 * np.sum(intensity) / self.nparticles
        if percentage < 50:
            warnings.warn(
                f"Only {percentage:.2f}% of the particles are shown "
                " on this synthetic radiograph. Consider increasing "
                " the size to include more.",
                RuntimeWarning,
            )

        if optical_density:
            # Generate the null radiograph
            x, y, I0 = self.synthetic_radiograph(size=size, bins=bins, null=True)

            # Calcualte I0 as the mean of the non-zero values in the null
            # histogram. Zeros are just outside of the illuminate area.
            I0 = np.mean(I0[I0 != 0])

            # Overwrite any zeros in intensity to avoid log10(0)
            intensity[intensity == 0] = 1

            # Calculate the optical_density
            intensity = -np.log10(intensity / I0)

        return h * u.m, v * u.m, intensity
