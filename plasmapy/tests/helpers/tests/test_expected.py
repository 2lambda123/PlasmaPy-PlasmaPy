"""Test the class responsible for checking and analyzing the expected result of a test."""

import collections
import pytest

from plasmapy.tests.helpers.expected import (
    _is_exception,
    _is_warning,
    _is_warning_and_value,
    ExpectedTestOutcome,
)
from plasmapy.utils.exceptions import PlasmaPyWarning

expected_exception = KeyError
expected_warning = UserWarning
expected_value = 42

Case = collections.namedtuple("Case", ["argument", "attribute", "correct_outcome"])

expected_value_and_warning = (expected_value, expected_warning)
expected_warning_and_value = (expected_warning, expected_value)

expected_outcome_test_cases = [
    Case(expected_exception, "expected_exception", expected_exception),
    Case(expected_exception, "expected_outcome", expected_exception),
    Case(expected_exception, "expecting_an_exception", True),
    Case(expected_exception, "expecting_a_warning", False),
    Case(expected_exception, "expecting_a_value", False),
    Case(expected_warning, "expected_warning", expected_warning),
    Case(expected_warning, "expected_outcome", expected_warning),
    Case(expected_warning, "expecting_an_exception", False),
    Case(expected_warning, "expecting_a_warning", True),
    Case(expected_warning, "expecting_a_value", False),
    Case(expected_value, "expected_value", expected_value),
    Case(expected_value, "expected_outcome", expected_value),
    Case(expected_value, "expecting_an_exception", False),
    Case(expected_value, "expecting_a_warning", False),
    Case(expected_value, "expecting_a_value", True),
    Case(expected_value_and_warning, "expected_warning", expected_warning),
    Case(expected_value_and_warning, "expected_value", expected_value),
    Case(expected_value_and_warning, "expecting_an_exception", False),
    Case(expected_value_and_warning, "expecting_a_warning", True),
    Case(expected_value_and_warning, "expecting_a_value", True),
    Case(expected_value_and_warning, "expected_outcome", expected_warning_and_value),
    Case(expected_warning_and_value, "expected_warning", expected_warning),
    Case(expected_warning_and_value, "expected_value", expected_value),
    Case(expected_warning_and_value, "expecting_an_exception", False),
    Case(expected_warning_and_value, "expecting_a_warning", True),
    Case(expected_warning_and_value, "expecting_a_value", True),
    Case(expected_warning_and_value, "expected_outcome", expected_warning_and_value),
]


@pytest.mark.parametrize("case", expected_outcome_test_cases)
def test_expected_test_outcome_attributes(case: Case):
    """Test that `ExpectedTestOutcome` attributes each return the expected values."""
    expected_outcome = ExpectedTestOutcome(case.argument)
    result = expected_outcome.__getattribute__(case.attribute)
    if result is not case.correct_outcome and result != case.correct_outcome:
        pytest.fail(
            f"ExpectedTestOutcome({case.argument}) results in {repr(result)} "
            f"but should result in {case.correct_outcome}."
        )


exception_to_be_raised = RuntimeError

exception_raising_cases = [
    Case(expected_exception, "expected_warning", exception_to_be_raised),
    Case(expected_exception, "expected_value", exception_to_be_raised),
    Case(expected_warning, "expected_exception", exception_to_be_raised),
    Case(expected_warning, "expected_value", exception_to_be_raised),
    Case(expected_value, "expected_exception", exception_to_be_raised),
    Case(expected_value, "expected_warning", exception_to_be_raised),
    Case(expected_value_and_warning, "expected_exception", exception_to_be_raised),
    Case(expected_warning_and_value, "expected_exception", exception_to_be_raised),
]


@pytest.mark.parametrize("case", exception_raising_cases)
def test_expected_test_outcome_exceptions(case: Case):
    """Test that attributes of `ExpectedTestOutcome` raise exceptions as needed."""
    if not issubclass(case.correct_outcome, Exception):
        raise TypeError(
            "Incorrect test setup: the expected outcome must be an exception."
        )
    with pytest.raises(case.correct_outcome):
        expected_outcome = ExpectedTestOutcome(case.argument)
        result = expected_outcome.__getattribute__(case.attribute)
        pytest.fail(
            f"The ExpectedTestOutcome instance for {case.argument} did not "
            f"raise the expected exception but instead returned {result}."
        )


is_warning_test_inputs = [
    (Warning, True),
    (UserWarning, True),
    (PlasmaPyWarning, True),
    (Exception, False),
    (BaseException, False),
    ("", False),
    ((Warning, 1), False),
]


@pytest.mark.parametrize("possible_warning, actually_a_warning", is_warning_test_inputs)
def test__is_warning(possible_warning, actually_a_warning: bool):
    """
    Test that `~plasmapy.utils.pytest_helpers.expected._is_warning`
    returns `True` for warnings and `False` for other objects.
    """
    interpreted_as_warning = _is_warning(possible_warning)
    if interpreted_as_warning != actually_a_warning:
        pytest.fail(
            f"_is_warning({repr(possible_warning)}) should return "
            f"{actually_a_warning}, but is instead returning "
            f"{interpreted_as_warning}."
        )


is_exception_test_inputs = [
    (Warning, False),
    (UserWarning, False),
    (Exception, True),
    (BaseException, True),
    ("", False),
]


@pytest.mark.parametrize(
    "possible_exception, actually_an_exception", is_exception_test_inputs
)
def test_is_exception(possible_exception, actually_an_exception: bool):
    """
    Test that `~plasmapy.utils.pytest_helpers.expected._is_exception`
    returns `True` for exceptions and `False` for other objects.
    """
    interpreted_as_exception = _is_exception(possible_exception)
    if interpreted_as_exception != actually_an_exception:
        pytest.fail(
            f"_is_exception({repr(possible_exception)} should return "
            f"{actually_an_exception}, but is instead returning "
            f"{interpreted_as_exception}."
        )


is_warning_and_value_test_inputs = [
    ((Warning, ""), True),
    (["", UserWarning], True),
    ((Warning, UserWarning), False),
    (Warning, False),
    (UserWarning, False),
    (Exception, False),
    (BaseException, False),
    ("", False),
]


@pytest.mark.parametrize(
    "possible_warning_and_value, actually_warning_and_value",
    is_warning_and_value_test_inputs,
)
def test__is_warning_and_value(
    possible_warning_and_value, actually_warning_and_value: bool
):
    """
    Test that `_is_warning_and_value` returns `True` for a `tuple` or
    `list` containing a warning and an `object` that is not a `Warning`,
    and `False` for anything else.
    """
    interpreted_as_warning_and_value = _is_warning_and_value(possible_warning_and_value)
    if interpreted_as_warning_and_value != actually_warning_and_value:
        pytest.fail(
            f"_is_warning_and_value returns {interpreted_as_warning_and_value} "
            f"with {repr(possible_warning_and_value)} as an argument, but is "
            f"expected to return {actually_warning_and_value}."
        )
