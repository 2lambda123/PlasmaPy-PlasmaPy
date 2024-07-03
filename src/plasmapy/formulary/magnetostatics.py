"""
Define MagneticStatics class to calculate common static magnetic fields
as first raised in issue #100.
"""

__all__ = [
    "CircularWire",
    "FiniteStraightWire",
    "GeneralWire",
    "InfiniteStraightWire",
    "MagneticDipole",
    "MagnetoStatics",
    "Wire",
]

import abc

import astropy.constants as const
import astropy.units as u
import numpy as np
import scipy.special

from plasmapy.utils.decorators import validate_quantities


class MagnetoStatics(abc.ABC):
    """Abstract class for magnetostatic fields."""

    @abc.abstractmethod
    def magnetic_field(self, p: u.Quantity[u.m]) -> u.Quantity[u.T]:
        """
        Calculate magnetic field generated by this wire at position ``p``.

        Parameters
        ----------
        p : `~astropy.units.Quantity`
            Three-dimensional position vector.

        Returns
        -------
        B : `~astropy.units.Quantity`
            Magnetic field at the specified position.
        """


class MagneticDipole(MagnetoStatics):
    r"""
    Simple magnetic dipole — two nearby opposite point charges.

    Parameters
    ----------
    moment : `~astropy.units.Quantity`
        Magnetic moment vector, in units of A m\ :sup:`2`\ .

    p0 : `~astropy.units.Quantity`
        Position of the dipole.
    """

    @validate_quantities
    def __init__(self, moment: u.Quantity[u.A * u.m**2], p0: u.Quantity[u.m]) -> None:
        self.moment = moment.value
        self._moment_u = moment.unit
        self.p0 = p0.value
        self._p0_u = p0.unit

    def __repr__(self) -> str:
        name = self.__class__.__name__
        moment = self.moment
        p0 = self.p0
        moment_u = self._moment_u
        p0_u = self._p0_u
        return f"{name}(moment={moment}{moment_u}, p0={p0}{p0_u})"

    def magnetic_field(self, p: u.Quantity[u.m]) -> u.Quantity[u.T]:
        r"""
        Calculate magnetic field from this magnetic dipole at position ``p``.

        Parameters
        ----------
        p : `~astropy.units.Quantity`
            Three-dimensional position vector.

        Returns
        -------
        B : `~astropy.units.Quantity`
            Magnetic field at the specified position.

        Notes
        -----
        The magnetic field generated by a magnetic dipole is calculated
        at a point in 3D space by taking the limit of a current loop as
        its radius shrinks to a point and keeping its magnetic moment
        constant.

        Let the point where the magnetic field will be calculated be
        represented by the point :math:`p` and the location of the
        dipole by the point :math:`p_0` (with associated position vectors
        :math:`\vec{p}` and :math:`\vec{p}_0`, respectively). Further,
        let the displacement vector from the dipole at point
        :math:`p_0` to the point :math:`p` be written as
        :math:`\vec{r} = \vec{p} - \vec{p}_0`.

        The magnetic field :math:`\vec{B}` from a magnetic dipole with
        a magnetic dipole moment :math:`\vec{m}` is then found
        at the point :math:`p` using the expression

        .. math::
            \vec{B} = \frac{\mu_0}{4\pi}
            \left( \frac{3(\vec{m} \cdot \vec{r})\vec{r}}{|\vec{r}|^5}
            - \frac{\vec{m}}{|\vec{r}|^3} \right)

        where :math:`\mu_0` is vacuum permeability.
        """
        r = p - self.p0
        m = self.moment
        B = (
            const.mu0.value
            / 4
            / np.pi
            * (
                3 * r * np.dot(m, r) / np.linalg.norm(r) ** 5
                - m / np.linalg.norm(r) ** 3
            )
        )
        return B * u.T


class Wire(MagnetoStatics):
    """Abstract wire class for concrete wires to be inherited from."""


class GeneralWire(Wire):
    r"""
    General wire class described by its parametric vector equation.

    Parameters
    ----------
    parametric_eq : Callable
        A vector-valued (with units of position) function of a single real
        parameter.

    t1 : `float`
        Lower bound of the parameter, smaller than ``t2``.

    t2 : `float`
        Upper bound of the parameter, larger than ``t1``.

    current: `~astropy.units.Quantity`
        Electric current.
    """

    @validate_quantities
    def __init__(self, parametric_eq, t1, t2, current: u.Quantity[u.A]) -> None:
        if callable(parametric_eq):
            self.parametric_eq = parametric_eq
        else:
            raise TypeError("Argument parametric_eq should be a callable")
        if t1 >= t2:
            raise ValueError(f"t1={t1} is not smaller than t2={t2}")
        self.t1 = t1
        self.t2 = t2
        self.current = current.value
        self._current_u = current.unit

    def __repr__(self) -> str:
        name = self.__class__.__name__
        parametric_eq = self.parametric_eq.__name__
        t1 = self.t1
        t2 = self.t2
        current = self.current
        current_u = self._current_u
        return (
            f"{name}(parametric_eq={parametric_eq}, t1={t1}, t2={t2}, "
            f"current={current}{current_u})"
        )

    def magnetic_field(self, p: u.Quantity[u.m], n: int = 1000) -> u.Quantity[u.T]:
        r"""
        Calculate magnetic field generated by this wire at position ``p``.

        Parameters
        ----------
        p : `~astropy.units.Quantity`
            Three-dimensional position vector.

        n : `int`, optional
            Number of segments for Wire calculation (defaults to 1000).

        Returns
        -------
        B : `astropy.units.Quantity`
            Magnetic field at the specified position.

        Notes
        -----
        The magnetic field generated by a wire with constant electric
        current is found at a point in 3D space by approximating the
        Biot–Savart law.

        Let the point where the magnetic field will be calculated be
        represented by the point :math:`p` (with associated position vector
        :math:`\vec{p}`) and the curve :math:`C` defining the wire by the
        parametric vector equation :math:`\vec{l}(t)` with
        :math:`t_{\min} \leq t \leq t_{\max}`. Further, let the
        displacement vector from the wire to the point :math:`p` be written
        as :math:`\vec{r}(t) = \vec{p} - \vec{l}(t)`.

        The magnetic field :math:`\vec{B}` generated by the wire with constant
        current :math:`I` at point :math:`p` can then be expressed using
        the Biot–Savart law, which takes the form

        .. math::
            \vec B = \frac{\mu_0 I}{4\pi}
            \int_C \frac{d\vec{l} \times \vec{r}}{|\vec{r}|^3}

        where :math:`\mu_0` is the permeability of free space.

        This line integral is approximated by segmenting the wire into
        :math:`n` straight pieces of equal length. The :math:`i\text{th}`
        wire element can be written as
        :math:`\Delta\vec{l}_i = \vec{l}(t_i) - \vec{l}(t_{i - 1})`
        where :math:`t_i = t_{\min} + i(t_{\max}-t_{\min})/n`. Further,
        the displacement vector from the center of the :math:`i\text{th}`
        wire element to the position :math:`\vec{p}` is
        :math:`\vec{r}_i = \vec{p} - \frac{\vec{l}(t_i) + \vec{l}(t_{i-1})}{2}`.

        The integral is then approximated as

        .. math::
            \vec B \approx \frac{\mu_0 I}{4\pi}
            \sum_{i=1}^{n}\frac{\vec{\Delta l}_i \times
            \vec{r}_i}{\left| \vec{r}_i \right|^3}.
        """

        p1 = self.parametric_eq(self.t1)
        step = (self.t2 - self.t1) / n
        t = self.t1
        B = 0
        for _ in range(n):  # noqa: B007
            t = t + step
            p2 = self.parametric_eq(t)
            dl = p2 - p1
            p1 = p2
            R = p - (p2 + p1) / 2
            B += np.cross(dl, R) / np.linalg.norm(R) ** 3
        B = B * const.mu0.value / 4 / np.pi * self.current
        return B * u.T


class FiniteStraightWire(Wire):
    """
    Finite length straight wire class.

    The ``p1`` to ``p2`` direction is the positive current direction.

    Parameters
    ----------
    p1 : `~astropy.units.Quantity`
        Three-dimensional Cartesian coordinate of one end of the straight wire.

    p2 : `~astropy.units.Quantity`
        Three-dimensional Cartesian coordinate of another end of the straight wire.

    current : `astropy.units.Quantity`
        Electric current.
    """

    @validate_quantities
    def __init__(
        self, p1: u.Quantity[u.m], p2: u.Quantity[u.m], current: u.Quantity[u.A]
    ) -> None:
        self.p1 = p1.value
        self.p2 = p2.value
        self._p1_u = p1.unit
        self._p2_u = p2.unit
        if np.all(p1 == p2):
            raise ValueError("p1, p2 should not be the same point.")
        self.current = current.value
        self._current_u = current.unit

    def __repr__(self) -> str:
        name = self.__class__.__name__
        p1 = self.p1
        p2 = self.p2
        current = self.current
        p1_u = self._p1_u
        p2_u = self._p2_u
        current_u = self._current_u
        return f"{name}(p1={p1}{p1_u}, p2={p2}{p2_u}, current={current}{current_u})"

    def magnetic_field(self, p) -> u.Quantity[u.T]:
        r"""
        Calculate magnetic field generated by this wire at position ``p``.

        Parameters
        ----------
        p : `astropy.units.Quantity`
            Three-dimensional position vector

        Returns
        -------
        B : `astropy.units.Quantity`
            Magnetic field at the specified position

        Notes
        -----
        The magnetic field generated by a straight, finite wire with
        constant electric current can be found at a point in 3D space
        using the Biot–Savart law.

        Let the point where the magnetic field will be calculated be
        represented by the point :math:`p_0` (or ``p``) and the wire's
        beginning and end as :math:`p_1` and :math:`p_2`, respectively
        (with corresponding position vectors :math:`\vec{p}_0`,
        :math:`\vec{p}_1`, and :math:`\vec{p}_2`, respectively).
        Further, the vector from points
        :math:`p_i` to :math:`p_j` can be written as
        :math:`\vec{p}_{ij} = \vec{p}_j - \vec{p}_i`.

        Next, consider the triangle with the points :math:`p_0`,
        :math:`p_1`, and :math:`p_2` as vertices. The vector from the
        vertex :math:`p_0` to the perpendicular foot opposite the
        vertex :math:`p_0`, which will be used to find the unit vector
        in the direction of the magnetic field, can be expressed as

        .. math::
            \vec{p}_f = \vec{p}_1 + \vec{p}_{12}
            \frac{\vec{p}_{10} \cdot \vec{p}_{12}}
            {|\vec{p}_{12}|^2}.

        The magnetic field :math:`\vec{B}` generated by the wire with
        current :math:`I` can be found at the point :math:`p_0` using
        the Biot–Savart law which in this case simplifies to

        .. math::
            \vec{B} = \frac{\mu_0 I}{4π} (\cos θ_1 - \cos θ_2)
            \hat{B}

        where :math:`\mu_0` is the permeability of free space,
        :math:`\theta_1` (:math:`\theta_2`) is the angle between
        :math:`\vec{p}_{10}` (:math:`\vec{p}_{20}`) and
        :math:`\vec{p}_{12}` with

        .. math::
            \cos\theta_1 = \frac{\vec{p}_{10} \cdot \vec{p}_{12}}
            {|\vec{p}_{10}| |\vec{p}_{12}|}, \quad
            \cos\theta_2 = \frac{\vec{p}_{20} \cdot \vec{p}_{12}}
            {|\vec{p}_{20}| |\vec{p}_{12}|},

        and

        .. math::
            \hat{B} = \frac{\vec{p}_{12} \times \vec{p}_{f0}}
            {|\vec{p}_{12} \times \vec{p}_{f0}|}

        is the unit vector in the direction of the magnetic field
        at the point :math:`p_0`.
        """
        # foot of perpendicular
        p1, p2 = self.p1, self.p2
        p2_p1 = p2 - p1
        ratio = np.dot(p - p1, p2_p1) / np.dot(p2_p1, p2_p1)
        pf = p1 + p2_p1 * ratio

        # angles: theta_1 = <p - p1, p2 - p1>, theta_2 = <p - p2, p2 - p1>
        cos_theta_1 = (
            np.dot(p - p1, p2_p1) / np.linalg.norm(p - p1) / np.linalg.norm(p2_p1)
        )
        cos_theta_2 = (
            np.dot(p - p2, p2_p1) / np.linalg.norm(p - p2) / np.linalg.norm(p2_p1)
        )

        B_unit = np.cross(p2_p1, p - pf)
        B_unit = B_unit / np.linalg.norm(B_unit)

        B = (
            B_unit
            / np.linalg.norm(p - pf)
            * (cos_theta_1 - cos_theta_2)
            * const.mu0.value
            / 4
            / np.pi
            * self.current
        )

        return B * u.T

    def to_GeneralWire(self):
        """Convert this `Wire` into a `GeneralWire`."""
        p1, p2 = self.p1, self.p2
        return GeneralWire(lambda t: p1 + (p2 - p1) * t, 0, 1, self.current * u.A)


class InfiniteStraightWire(Wire):
    """
    Infinite straight wire class.

    Parameters
    ----------
    direction:
        Three-dimensional direction vector of the wire, also the
        positive current direction.

    p0 : `~astropy.units.Quantity`
        One point on the wire.

    current : `~astropy.units.Quantity`
        Electric current.
    """

    @validate_quantities
    def __init__(
        self, direction, p0: u.Quantity[u.m], current: u.Quantity[u.A]
    ) -> None:
        self.direction = direction / np.linalg.norm(direction)
        self.p0 = p0.value
        self._p0_u = p0.unit
        self.current = current.value
        self._current_u = current.unit

    def __repr__(self) -> str:
        name = self.__class__.__name__
        direction = self.direction
        p0 = self.p0
        current = self.current
        p0_u = self._p0_u
        current_u = self._current_u
        return (
            f"{name}(direction={direction}, p0={p0}{p0_u}, "
            f"current={current}{current_u})"
        )

    def magnetic_field(self, p) -> u.Quantity[u.T]:
        r"""
        Calculate magnetic field generated by this wire at position ``p``.

        Parameters
        ----------
        p : `astropy.units.Quantity`
            Three-dimensional position vector.

        Returns
        -------
        B : `astropy.units.Quantity`
            Magnetic field at the specified position.

        Notes
        -----
        The magnetic field generated by a straight wire with infinite
        length and constant electric current is found at a point in 3D
        space using the Biot–Savart law.

        Let the point where the magnetic field will be calculated be
        represented by the point :math:`p`, a point on the wire by
        :math:`p_0`, and the direction of the wire as the vector
        :math:`\vec{l}`. The magnetic field :math:`\vec{B}` generated by the
        wire with constant current :math:`I` at point :math:`p` is
        then expressed using the Biot–Savart law which takes the form

        .. math::
            \vec{B} = \frac{\mu_0 I}{2\pi |\vec{r}|} \hat{B}

        where :math:`\mu_0` is the permeability of free space,
        :math:`|\vec{r}| = |\vec{l} \times (\vec{p} - \vec{p}_0)|`
        is the perpendicular distance between the wire and the point
        :math:`p`, and

        .. math::
            \hat{B} = \frac{\vec{l} \times (\vec{p} - \vec{p}_0)}
            {|\vec{l} \times (\vec{p} - \vec{p}_0)|}

        is the unit vector in the direction of the magnetic field
        at point :math:`p`.
        """
        r = np.cross(self.direction, p - self.p0)
        B_unit = r / np.linalg.norm(r)
        r = np.linalg.norm(r)

        return B_unit / r * const.mu0.value / 2 / np.pi * self.current * u.T


class CircularWire(Wire):
    """
    Circular wire (coil) class.

    Parameters
    ----------
    normal :
        Three-dimensional normal vector of the circular coil.

    center : `~astropy.units.Quantity`
        Three-dimensional position vector of the circular coil's center.

    radius: `~astropy.units.Quantity`
        Radius of the circular coil.

    current: `~astropy.units.Quantity`
        Electric current.
    """

    def __repr__(self) -> str:
        name = self.__class__.__name__
        normal = self.normal
        center = self.center
        radius = self.radius
        current = self.current
        center_u = self._center_u
        radius_u = self._radius_u
        current_u = self._current_u
        return (
            f"{name}(normal={normal}, center={center}{center_u}, "
            f"radius={radius}{radius_u}, current={current}{current_u})"
        )

    @validate_quantities
    def __init__(
        self,
        normal,
        center: u.Quantity[u.m],
        radius: u.Quantity[u.m],
        current: u.Quantity[u.A],
        n: int = 300,
    ) -> None:
        self.normal = normal / np.linalg.norm(normal)
        self.center = center.value
        self._center_u = center.unit
        if radius > 0:
            self.radius = radius.value
            self._radius_u = radius.unit
        else:
            raise ValueError("Radius should be larger than 0")
        self.current = current.value
        self._current_u = current.unit

        # parametric equation
        # find other two axes in the disc plane
        z = np.array([0, 0, 1])
        axis_x = np.cross(z, self.normal)
        axis_y = np.cross(self.normal, axis_x)

        if np.linalg.norm(axis_x) == 0:
            axis_x = np.array([1, 0, 0])
            axis_y = np.array([0, 1, 0])
        else:
            axis_x = axis_x / np.linalg.norm(axis_x)
            axis_y = axis_y / np.linalg.norm(axis_y)

        self.axis_x = axis_x
        self.axis_y = axis_y

        def curve(t):
            if not isinstance(t, np.ndarray):
                return (
                    self.radius * (np.cos(t) * axis_x + np.sin(t) * axis_y)
                    + self.center
                )
            t = np.expand_dims(t, 0)
            axis_x_mat = np.expand_dims(axis_x, 1)
            axis_y_mat = np.expand_dims(axis_y, 1)
            return self.radius * (
                np.matmul(axis_x_mat, np.cos(t)) + np.matmul(axis_y_mat, np.sin(t))
            ) + np.expand_dims(self.center, 1)

        self.curve = curve

        self.roots_legendre = scipy.special.roots_legendre(n)
        self.n = n

    def magnetic_field(self, p) -> u.Quantity[u.T]:
        r"""
        Calculate magnetic field generated by this wire at position ``p``.

        Parameters
        ----------
        p : `~astropy.units.Quantity`
            Three-dimensional position vector.

        Returns
        -------
        B : `~astropy.units.Quantity`
            Magnetic field at the specified position.

        Notes
        -----
        The magnetic field generated by a circular wire with constant
        electric current is found at a point in 3D space using the
        Biot–Savart law. The integral in the Biot–Savart law is
        approximated using the Gauss–Legendre quadrature.

        Let the point where the magnetic field will be calculated be
        represented by the point :math:`p` and the wire be represented by
        the parametric vector equation

        .. math::
            \vec{l}(\theta) =
            R\cos\theta \hat{x} + R\sin\theta \hat{y},\quad
            -\pi \leq \theta \leq \pi

        where :math:`R` is the radius of the circular wire.
        Further, let the displacement vector from a point on the wire
        to the point :math:`p` be written as
        :math:`\vec{r}(\theta) = \vec{p} - \vec{l}(\theta)`.

        The magnetic field :math:`B` due to a current :math:`I` is
        then found at the point :math:`p` using the Biot–Savart law,
        which takes the form

        .. math::
            \vec{B} = \frac{\mu_0 I}{4\pi}
            \int_C \frac{d\vec{l} \times \vec{r}}{|\vec{r}|^3}.

        This line integral is approximated using the Gauss–Legendre
        quadrature with :math:`n` sample points:

        .. math::
            \hat{B} \approx \frac{\mu_0 I}{4\pi} \sum_{i=1}^n w_i
            \frac{\Delta\vec{l}(\pi x_i) \times \vec{r}(\pi x_i)}
            {|\vec{r}(\pi x_i)|^3}

        where :math:`w_i` is the :math:`i\text{th}` quadrature weight and
        :math:`x_i` is the :math:`i\text{th}` root of the :math:`n\text{th}`
        Legendre polynomial.
        """
        x, w = self.roots_legendre
        t = x * np.pi
        pt = self.curve(t)
        dl = self.radius * (
            -np.matmul(np.expand_dims(self.axis_x, 1), np.expand_dims(np.sin(t), 0))
            + np.matmul(np.expand_dims(self.axis_y, 1), np.expand_dims(np.cos(t), 0))
        )  # (3, n)

        r = np.expand_dims(p, 1) - pt  # (3, n)
        r_norm_3 = np.linalg.norm(r, axis=0) ** 3
        ft = np.cross(dl, r, axisa=0, axisb=0) / np.expand_dims(r_norm_3, 1)  # (n, 3)

        return (
            np.pi
            * np.matmul(np.expand_dims(w, 0), ft).squeeze(0)
            * const.mu0.value
            / 4
            / np.pi
            * self.current
            * u.T
        )

    def to_GeneralWire(self):
        """Convert this `Wire` into a `GeneralWire`."""
        return GeneralWire(self.curve, -np.pi, np.pi, self.current * u.A)
