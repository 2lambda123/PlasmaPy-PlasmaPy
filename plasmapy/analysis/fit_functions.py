"""
`FitFunction` classes designed to assist in curve fitting of swept Langmuir
traces.
"""
__all__ = [
    "AbstractFitFunction",
    "Exponential",
    "ExponentialPlusLinear",
    "ExponentialPlusOffset",
    "Linear",
]

import numpy as np

from abc import ABC, abstractmethod
from collections import namedtuple
from scipy.stats import linregress
from scipy.optimize import curve_fit, fsolve
from typing import Tuple, Union


class AbstractFitFunction(ABC):
    """
    Abstract class for defining fit functions :math:`f(x)` and the tools for
    fitting the function to a set of data.  These were originally designed for
    assisting in fitting curves to swept Langmuir data.
    """

    _param_names = NotImplemented  # type: Tuple[str, ...]

    def __init__(
            self,
            params: Tuple[float, ...] = None,
            param_errors: Tuple[float, ...] = None,
    ):
        """
        Parameters
        ----------
        params: Tuple[float, ...], optional
            Tuple of values for the function parameters. Equal in size to
            :attr:`param_names`.

        param_errors: Tuple[float, ...], optional
            Tuple of values for the errors associated with the function
            parameters.  Equal in size to :attr:`param_names`.

        """

        self.FitParamTuple = namedtuple("FitParamTuple", self._param_names)
        """
        A named tuple class used for attributes :attr:`params` and 
        :attr:`param_errors`.  The attribute :attr:`parameter_names` defines
        the tuple field names.
        """

        if params is None:
            self._params = None
        else:
            self.params = params

        if param_errors is None:
            self._param_errors = None
        else:
            self.param_errors = param_errors

        self._covariance_matrix = None
        self._rsq = None
        self._curve_fit_results = None

    def __call__(self, x, x_err=None, reterr=False):
        """
        Direct call of the fit function :math:`f(x)``.

        Parameters
        ----------
        x: array_like
            Dependent variables.

        x_err: array_like, optional
            Errors associated with the independent variables `x`.  Must be of
            size one or equal to the size of `x`.

        reterr: bool, optional
            (Default: `False`) If `True`, return an array of uncertainties
            associated with the calculated independent variables

        Returns
        -------
        y: `numpy.ndarray`
            Corresponding dependent variables :math:`y=f(x)` of the independent
            variables :math:`x`.

        y_err: `numpy.ndarray`
            Uncertainties associated with the calculated dependent variables
            :math:`\\delta y`
        """
        if not isinstance(x, np.ndarray):
            x = np.array(x)

        if reterr:
            try:
                y_err, y = self.func_err(x, x_err=x_err, rety=True)
            except NotImplementedError:
                y = self.func(x, *self.params)
                y_err = np.tile(np.nan, x.shape)

            return y, y_err

        y = self.func(x, *self.params)

        return y

    def __repr__(self):
        return f"{self.__str__()} {self.__class__}"

    @abstractmethod
    def __str__(self):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def func(x, *args):
        """
        The fit function.  This signature of the function must first take the
        independent variable followed by the parameters to be fitted as
        separate arguments.

        When sub-classing the definition should look something like::

            def func(x, a, b, c):
                return a * x ** 2 + b * x + c

        Parameters
        ----------
        x: array_like
            Independent variables to be passed to the fit function.

        *args
            The parameters that will be adjusted to make the fit.

        Returns
        -------
        `numpy.ndarray`:
            The calculated dependent variables of the independent variables `x`.
        """
        raise NotImplementedError

    @abstractmethod
    def func_err(self, x, x_err=None, rety=False):
        """
        Calculate dependent variable uncertainties :math:`\\delta y` for
        dependent variables :math:`y=f(x)`.

        Parameters
        ----------
        x: array_like
            Independent variables to be passed to the fit function.

        x_err: array_like, optional
            Errors associated with the independent variables `x`.  Must be of
            size one or equal to the size of `x`.

        rety: bool
            Set `True` to also return the associated dependent variables
            :math:`y = f(x)`.

        Returns
        -------
        err: `numpy.ndarray`
            The calculated uncertainties :math:`\\delta y` of the dependent
            variables (:math:`y = f(x)`) of the independent variables `x`.

        y: `numpy.ndarray`, optional
            (if `rety = True`) The associated dependent variables
            :math:`y = f(x)`.

        """
        raise NotImplementedError

    @property
    def curve_fit_results(self):
        """
        The results returned by the curve fitting routine used by
        :attr:`curve_fit`.  This is typically from `scipy.stats.linregress` or
        `scipy.optimize.curve_fit`.
        """
        return self._curve_fit_results

    @property
    def params(self) -> Union[None, tuple]:
        """The fitted parameters for the fit function."""
        if self._params is None:
            return self._params
        else:
            return self.FitParamTuple(*self._params)

    @params.setter
    def params(self, val) -> None:
        if isinstance(val, self.FitParamTuple):
            self._params = tuple(val)
        elif isinstance(val, (tuple, list)) and len(val) == len(self.param_names):
            self._params = tuple(val)
        else:
            raise ValueError(f"Got type {type(val)} for 'val', expecting tuple of "
                             f"length {len(self.param_names)}.")

    @property
    def param_errors(self) -> Union[None, tuple]:
        """The associated errors of the fit `parameters`."""
        if self._param_errors is None:
            return self._param_errors
        else:
            return self.FitParamTuple(*self._param_errors)

    @param_errors.setter
    def param_errors(self, val) -> None:
        if isinstance(val, self.FitParamTuple):
            self._param_errors = tuple(val)
        elif isinstance(val, (tuple, list)) and len(val) == len(self.param_names):
            self._param_errors = tuple(val)
        else:
            raise ValueError(f"Got type {type(val)} for 'val', expecting tuple of "
                             f"length {len(self.param_names)}.")

    @property
    def param_names(self) -> Tuple[str, ...]:
        """Names of the fitted parameters."""
        return self._param_names

    @property
    @abstractmethod
    def latex_str(self) -> str:
        """Latex friendly representation of the fit function."""
        raise NotImplementedError

    def root_solve(self, x0, **kwargs):
        """
        Solve for the root of the fit function (i.e. :math:`f(x_r) = 0`).  This
        mehtod used `scipy.optimize.fsolve` to find the function roots.

        Parameters
        ----------
        x0: `~numpy.ndarray`
            The starting estimate for the roots of :math:`f(x_r) = 0`.

        **kwargs
            Any keyword accepted by `scipy.optimize.fsolve`, except for `args`.

        Returns
        -------
        x : `~numpy.ndarray`
            The solution (or the result of the last iteration for an
            unsuccessful call).

        x_err: `~numpy.ndarray`
            The uncertainty associated with the root calculation.  **Currently
            this returns an array of** `numpy.nan` **values equal in shape to**
            `x` **, since there is no determined way to calculate the
            uncertaintyes.**

        Notes
        -----
        If the full output of `scipy.optimize.fsolve` is desired then one can do

            >>> import numpy as np
            >>> import scipy

            >>> class SomeFunc(AbstractFitFunction):
            ...     _param_names = ("m", "b")
            ...
            ...     def __str__(self):
            ...         return "f(x) = m x + b"
            ...
            ...     @property
            ...     def latex_str(self) -> str:
            ...         return f"m \\, x + b"
            ...
            ...     @staticmethod
            ...     def func(x, m, b):
            ...         return m * x + b
            ...
            ...     def func_err(self, x, x_err=None, rety=False):
            ...         m, b = self.params
            ...         m_err, b_err = self.param_errors
            ...
            ...         m_term = x * m_err
            ...         b_term = b_err
            ...         err = m_term ** 2 + b_term ** 2
            ...
            ...         if x_err is not None:
            ...             x_term = m * x_err
            ...             err += x_term ** 2
            ...         err = np.sqrt(err)
            ...
            ...         if rety:
            ...             y = self.func(x, m, b)
            ...             return err, y
            ...
            ...         return err
            ...
            >>> func = SomeFunc()
            >>> func.params = (1., 5.)
            >>> func.param_errors = (0.0, 0.0)
            >>> roots = scipy.optimize.fsolve(func, -4., full_output=True)
            >>> roots
            (array([-5.]),
             {'nfev': 4,
              'fjac': array([[-1.]]),
              'r': array([-1.]),
              'qtf': array([2.18...e-12]),
              'fvec': array([0.])},
             1,
             'The solution converged.')

        """
        kwargs["args"] = self.params
        results = fsolve(self.func, x0, **kwargs)
        if isinstance(results, tuple):
            results = results[0]

        return results, np.tile(np.nan, results.shape)

    @property
    def rsq(self):
        """
        Coefficient of determination (r-squared) value of the fit.

        .. math::

            r^2 &= 1 - \\frac{SS_{res}}{SS_{tot}}

            SS_{res} &= \\sum\\limits_{i} (y_i - f(x_i))^2

            SS_{tot} &= \\sum\\limits_{i} (y_i - \\bar{y})^2

        where :math:`(x_i, y_i)` are the sample data pairs, :math:`f(x_i)` is
        the fitted dependent variable corresponding to :math:`x_i`, and
        :math:`\\bar{y}` is the average of the :math:`y_i` values.

        """
        return self._rsq

    def curve_fit(self, xdata, ydata, **kwargs) -> None:
        """
        Use a non-linear least squares method to fit the fit function to
        (`xdata`, `ydata`), using `scipy.optimize.curve_fit`.  This will set
        the attributes :attr:`parameters`, :attr:`parameters_err`, and
        :attr:`rsq`.

        The results of `scipy.optimize.curve_fit` can be obtained via
        :attr:`curve_fit_results`.

        Parameters
        ----------
        xdata: array_like
            The independent variable where data is measured.  Should be 1D of
            length M.

        ydata: array_like
            The dependent data associated with `xdata`.

        **kwargs
            Any keywords accepted by `scipy.optimize.curve_fit`.

        Raises
        ------
        ValueError
            if either `ydata` or `xdata` contain NaNs, or if incompatible options
            are used.

        RuntimeError
            if the least-squares minimization fails.

        ~scipy.optimize.OptimizeWarning
            if covariance of the parameters can not be estimated.

        """
        popt, pcov = curve_fit(self.func, xdata, ydata, **kwargs)
        self._curve_fit_results = (popt, pcov)
        self.params = tuple(popt.tolist())
        self.param_errors = tuple(np.sqrt(np.diag(pcov)).tolist())

        # calc rsq
        # rsq = 1 - (ss_res / ss_tot)
        residuals = ydata - self.func(xdata, *self.params)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((ydata - np.mean(ydata)) ** 2)
        self._rsq = 1 - (ss_res / ss_tot)


class Exponential(AbstractFitFunction):
    """
    A sub-class of `AbstractFitFunction` to represent an exponential with an
    offset.

    .. math::

        y &= f(x) = A \\, e^{\\alpha \\, x}

        \\left( \\frac{\\delta y}{|y|} \\right)^2 &=
            \\left( \\frac{\\delta A}{A} \\right)^2
            + (x \\, \\delta \\alpha)^2
            + (\\alpha \\, \\delta x)^2

    where :math:`A` and :math:`\\alpha` are the real constants to be fitted and
    :math:`x` is the independent variable.  :math:`\\delta A`,
    :math:`\\delta \\alpha`, and :math:`\\delta x` are the respective
    uncertainties for :math:`A`, :math:`\\alpha`, and :math:`x`.
    """
    _param_names = ("a", "alpha")

    def __str__(self):
        return f"f(x) = A exp(alpha x)"

    @staticmethod
    def func(x, a, alpha):
        return a * np.exp(alpha * x)

    def func_err(self, x, x_err=None, rety=False):
        a, alpha = self.params
        a_err, alpha_err = self.param_errors
        y = self.func(x, a, alpha)

        a_term = (a_err / a) ** 2
        alpha_term = (x * alpha_err) ** 2

        err = a_term + alpha_term

        if x_err is not None:
            x_term = (alpha * x_err) ** 2
            err += x_term

        err = np.abs(y) * np.sqrt(err)

        if rety:
            return err, y

        return err

    @property
    def latex_str(self) -> str:
        return fr"A \, \exp(\alpha \, x)"

    def root_solve(self, *args, **kwargs):
        """
        The root :math:`f(x_r) = 0` for the fit function. **An exponential has no
        real roots.**

        Parameters
        ----------
        *args
            Not needed.  This is to ensure signature comparability with
            `AbstractFitFunction`.

        *kwargs
            Not needed.  This is to ensure signature comparability with
            `AbstractFitFunction`.

        Returns
        -------
        root: float
            The root value for the given fit :attr:`parameters`.

        err: float
            The uncertainty in the calculated root for the given fit
            :attr:`parameters` and :attr:`parameters_err`.
        """

        return np.nan, np.nan


class Linear(AbstractFitFunction):
    """
    A sub-class of `AbstractFitFunction` to represent a linear function.

    .. math::

        y &= f(x) = m \\, x + b

        (\\delta y)^2 &= (x \\, \\delta m)^2 + (m \\, \\delta x)^2 + (\\delta b)^2

    where :math:`m` and :math:`b` are real constants to be fitted and :math:`x` is
    the independent variable.  :math:`\\delta m`, :math:`\\delta b`, and
    :math:`\\delta x` are the respective uncertainties for :math:`m`, :math:`b`,
    and :math:`x`.
    """

    _param_names = ("m", "b")

    def __str__(self):
        return f"f(x) = m x + b"

    @staticmethod
    def func(x, m, b):
        """
        The fit function, a linear function.

        .. math::

            f(x) = m \\, x + b

        where :math:`m` and :math:`b` are positive real constants representing the
        slope and intercept, respectively, and :math:`x` is the independent
        variable.

        Parameters
        ----------
        x: array_like
            Independent variable.
        m: float
            value for slope :math:`m`

        b: float
            value for intercept :math:`b`

        Returns
        -------
        y: array_like
            dependent variables corresponding to :math:`x`

        """
        return m * x + b

    def func_err(self, x, x_err=None, rety=False):
        """
        Calculate dependent variable uncertainties :math:`\\delta y` for
        dependent variables :math:`y=f(x)`.

        .. math::

            (\\delta y)^2 &= (x \\, \\delta m)^2 + (m \\, \\delta x)^2 + (\\delta b)^2

        Parameters
        ----------
        x: array_like
            Independent variables to be passed to the fit function.

        Returns
        -------
        `numpy.ndarray`:
            The calculated uncertainty of the dependent variables of the
            independent variables `x`.
        """
        m, b = self.params
        m_err, b_err = self.param_errors

        m_term = (m_err * x) ** 2
        b_term = b_err ** 2
        err = m_term + b_term

        if x_err is not None:
            x_term = (m * x_err) ** 2
            err += x_term
        err = np.sqrt(err)

        if rety:
            y = self.func(x, m, b)
            return err, y

        return err

    @property
    def latex_str(self) -> str:
        return fr"m \, x + b"

    @property
    def rsq(self):
        """
        Coefficient of determination (r-squared) value of the fit.  Calculated
        by `scipy.stats.linregress` from the fit.
        """
        return self._rsq

    def root_solve(self, *args, **kwargs):
        """
        The root :math:`f(x_r) = 0` for the fit function.

        .. math::

            x_r &= \\frac{-b}{m}

            \\delta x_r &= |x_r| \\sqrt{
                \\left( \\frac{\\delta m}{m} \\right)^2
                + \\left( \\frac{\\delta b}{b} \\right)^2
            }

        Parameters
        ----------
        *args
            Not needed.  This is to ensure signature comparability with
            `AbstractFitFunction`.

        *kwargs
            Not needed.  This is to ensure signature comparability with
            `AbstractFitFunction`.

        Returns
        -------
        root: float
            The root value for the given fit :attr:`parameters`.

        err: float
            The uncertainty in the calculated root for the given fit
            :attr:`parameters` and :attr:`parameters_err`.
        """
        m, b = self.params
        root = -b / m

        m_err, b_err = self.param_errors
        err = np.abs(root) * np.sqrt((m_err / m) ** 2 + (b_err / b) ** 2)

        return root, err

    def curve_fit(self, xdata, ydata, **kwargs) -> None:
        """
        Calculate a linear least-squares regression of (`xdata`, `ydata`) using
        `scipy.stats.linregress`.  This will set the attributes
        :attr:`parameters`, :attr:`parameters_err`, and :attr:`rsq`.

        The results of `scipy.stats.linregress` can be obtained via
        :attr:`curve_fit_results`.

        Parameters
        ----------
        xdata: array_like
            The independent variable where data is measured.  Should be 1D of
            length M.

        ydata: array_like
            The dependent data associated with `xdata`.

        **kwargs
            Any keywords accepted by `scipy.stats.linregress.curve_fit`.

        """
        results = linregress(xdata, ydata)
        self._curve_fit_results = results

        m = results[0]
        b = results[1]
        self.params = (m, b)

        m_err = results[4]
        b_err = np.sum(xdata ** 2) - ((np.sum(xdata) ** 2) / xdata.size)
        b_err = m_err * np.sqrt(1.0 / b_err)
        self.param_errors = (m_err, b_err)

        self._rsq = results[2] ** 2


class ExponentialPlusLinear(AbstractFitFunction):
    """
    A sub-class of `AbstractFitFunction` to represent an exponential with an
    linear offset.

    .. math::

        y =& f(x) = A \\, e^{\\alpha \\, x} + m \\, x + b\\\\
        (\\delta y)^2 =&
            \\left( A e^{\\alpha x}\\right)^2 \\left[
                \\left( \\frac{\\delta A}{A} \\right)^2
                + (x \\, \\delta \\alpha)^2
                + (\\alpha \\, \\delta x)^2
            \\right]\\\\
            & + \\left(2 \\, A \\, \\alpha \\, m \\, e^{\\alpha x}\\right)
                (\\delta x)^2\\\\
            & + \\left[(x \\, \\delta m)^2 + (\\delta b)^2 +(m \\, \\delta x)^2\\right]

    where :math:`A`, :math:`\\alpha`, :math:`m`, and :math:`b` are the real
    constants to be fitted and :math:`x` is the independent variable.
    :math:`\\delta A`, :math:`\\delta \\alpha`, :math:`\\delta m`, :math:`\\delta b`,
    and :math:`\\delta x` are the respective uncertainties for :math:`A`,
    :math:`\\alpha`, :math:`m`, and :math:`b`, and :math:`x`.
    """
    _param_names = ("a", "alpha", "m", "b")

    def __init__(self):
        super().__init__()
        self._exponential = Exponential()
        self._linear = Linear()

    def __str__(self):
        exp_str = self._exponential.__str__().lstrip("f(x) = ")
        lin_str = self._linear.__str__().lstrip("f(x) = ")
        return f"f(x) = {exp_str} + {lin_str}"

    @property
    def latex_str(self) -> str:
        exp_str = self._exponential.latex_str
        lin_str = self._linear.latex_str
        return fr"{exp_str} + {lin_str}"

    @AbstractFitFunction.params.setter
    def params(self, val) -> None:
        AbstractFitFunction.params.fset(self, val)
        self._exponential.params = (self.params.a, self.params.alpha)
        self._linear.params = (self.params.m, self.params.b)

    @AbstractFitFunction.param_errors.setter
    def param_errors(self, val) -> None:
        AbstractFitFunction.param_errors.fset(self, val)
        self._exponential.param_errors = (
            self.param_errors.a,
            self.param_errors.alpha,
        )
        self._linear.param_errors = (self.param_errors.m, self.param_errors.b)

    def func(self, x, a, alpha, m, b):
        exp_term = self._exponential.func(x, a, alpha)
        lin_term = self._linear.func(x, m, b)
        return exp_term + lin_term

    def func_err(self, x, x_err=None, rety=False):
        a, alpha, m, b = self.params

        exp_y, exp_err = self._exponential(x, x_err=x_err, reterr=True)
        lin_y, lin_err = self._linear(x, x_err=x_err, reterr=True)
        err = exp_err ** 2 + lin_err ** 2

        if x_err is not None:
            blend_err = 2 * a * alpha * m * np.exp(alpha * x) * (x_err ** x)
            err += blend_err
        err = np.sqrt(err)

        if rety:
            return err, exp_y + lin_y

        return err


class ExponentialPlusOffset(AbstractFitFunction):
    """
    A sub-class of `AbstractFitFunction` to represent an exponential with a DC
    offset.

    .. math::

        y =& f(x) = A \\, e^{\\alpha \\, x} + m \\, x + b\\\\
        (\\delta y)^2 =&
            \\left( A e^{\\alpha x}\\right)^2 \\left[
                \\left( \\frac{\\delta A}{A} \\right)^2
                + (x \\, \\delta \\alpha)^2
                + (\\alpha \\, \\delta x)^2
            \\right]
            + (\\delta b)^2


    where :math:`A`, :math:`\\alpha`, and :math:`b` are the real constants to
    be fitted and :math:`x` is the independent variable.  :math:`\\delta A`,
    :math:`\\delta \\alpha`, :math:`\\delta b`, and :math:`\\delta x` are the
    respective uncertainties for :math:`A`, :math:`\\alpha`, and :math:`b`, and
    :math:`x`.

    """
    _param_names = ("a", "alpha", "b")

    def __init__(self):
        super().__init__()
        self._explin = ExponentialPlusLinear()

    def __str__(self):
        return f"f(x) = A exp(alpha x) + b"

    @property
    def latex_str(self) -> str:
        return fr"A \, \exp(B \, x) + C"

    @AbstractFitFunction.params.setter
    def params(self, val) -> None:
        AbstractFitFunction.params.fset(self, val)
        self._explin.params = (
            self.params.a,
            self.params.alpha,
            0.0,
            self.params.b,
        )

    @AbstractFitFunction.param_errors.setter
    def param_errors(self, val) -> None:
        AbstractFitFunction.param_errors.fset(self, val)
        self._explin.param_errors = (
            self.param_errors.a,
            self.param_errors.alpha,
            0.0,
            self.param_errors.b,
        )

    def func(self, x, a, alpha, b):
        return self._explin.func(x, a, alpha, 0.0, b)

    def func_err(self, x, x_err=None, rety=False):
        y, err = self._explin(x, x_err=x_err, reterr=True)

        if rety:
            return err, y

        return err

    def root_solve(self, *args, **kwargs):
        """
        The root :math:`f(x_r) = 0` for the fit function.

        .. math::

            x_r &= \\frac{1}{\\alpha} \\ln \\left( \\frac{-b}{A} \\right)

            \\delta x_r &= \\sqrt{
                \\left( \\frac{1}{\\alpha} \\frac{\\delta A}{A} \\right)^2
                + \\left( x_r \\frac{\\delta \\alpha}{\\alpha} \\right)^2
                + \\left( \\frac{1}{\\alpha} \\frac{\\delta b}{b} \\right)^2
            }

        Parameters
        ----------
        *args
            Not needed.  This is to ensure signature comparability with
            `AbstractFitFunction`.

        *kwargs
            Not needed.  This is to ensure signature comparability with
            `AbstractFitFunction`.

        Returns
        -------
        root: float
            The root value for the given fit :attr:`parameters`.

        err: float
            The uncertainty in the calculated root for the given fit
            :attr:`parameters` and :attr:`parameters_err`.
        """
        a, alpha, b = self.params
        a_err, b_err, c_err = self.param_errors

        root = np.log(-b / a) / alpha

        a_term = a_err / (a * alpha)
        b_term = b_err * root / alpha
        c_term = c_err / (alpha * b)
        err = np.sqrt(a_term ** 2 + b_term ** 2 + c_term ** 2)

        return root, err
