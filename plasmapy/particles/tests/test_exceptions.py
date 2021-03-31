# IonizationStateCollection

tests_for_exceptions = {
    "wrong type": IE({"inputs": None}, ParticleError),
    "not normalized": IE(
        {"inputs": {"He": [0.4, 0.5, 0.0]}, "tol": 1e-9}, ParticleError
    ),
    "negative ionfrac": IE({"inputs": {"H": [-0.1, 1.1]}}, ParticleError),
    "ion": IE({"inputs": {"H": [0.1, 0.9], "He+": [0.0, 0.9, 0.1]}}, ParticleError),
    "repeat elements": IE(
        {"inputs": {"H": [0.1, 0.9], "hydrogen": [0.2, 0.8]}}, ParticleError
    ),
    "isotope of element": IE(
        {"inputs": {"H": [0.1, 0.9], "D": [0.2, 0.8]}}, ParticleError
    ),
    "negative abundance": IE(
        {
            "inputs": {"H": [0.1, 0.9], "He": [0.4, 0.5, 0.1]},
            "abundances": {"H": 1, "He": -0.1},
        },
        ParticleError,
    ),
    "imaginary abundance": IE(
        {
            "inputs": {"H": [0.1, 0.9], "He": [0.4, 0.5, 0.1]},
            "abundances": {"H": 1, "He": 0.1j},
        },
        ParticleError,
    ),
    "wrong density units": IE(
        {
            "inputs": {"H": [10, 90] * u.m ** -3, "He": [0.1, 0.9, 0] * u.m ** -2},
            "abundances": {"H": 1, "He": 0.1},
        },
        ParticleError,
    ),
    "abundance redundance": IE(
        {
            "inputs": {"H": [10, 90] * u.m ** -3, "He": [0.1, 0.9, 0] * u.m ** -3},
            "abundances": {"H": 1, "He": 0.1},
        },
        ParticleError,
    ),
    "abundance contradiction": IE(
        {
            "inputs": {"H": [10, 90] * u.m ** -3, "He": [0.1, 0.9, 0] * u.m ** -3},
            "abundances": {"H": 1, "He": 0.11},
        },
        ParticleError,
    ),
    "kappa too small": IE({"inputs": ["H"], "kappa": 1.499999}, ParticleError),
    "negative n": IE({"inputs": ["H"], "n0": -1 * u.cm ** -3}, ParticleError),
    "negative T_e": IE({"inputs": ["H-1"], "T_e": -1 * u.K}, ParticleError),
}


@pytest.mark.parametrize("test_name", tests_for_exceptions.keys())
def test_exceptions_upon_instantiation(test_name):
    """
    Test that appropriate exceptions are raised for inappropriate inputs
    to IonizationStateCollection when first instantiated.
    """
    run_test(
        IonizationStateCollection,
        kwargs=tests_for_exceptions[test_name].inputs,
        expected_outcome=tests_for_exceptions[test_name].expected_exception,
    )


# from test_atomic.py




# The tables above do not include the function to be tested in order to
# avoid cluttering up the code.  The following block of code prepends
# the correct function to each list containing args, kwargs, and the
# expected outcome prior to being passed through to run_test.


tables_and_functions = [
    (atomic_symbol, atomic_symbol_table),
    (isotope_symbol, isotope_symbol_table),
    (atomic_number, atomic_number_table),
    (mass_number, mass_number_table),
    (element_name, element_name_table),
    (standard_atomic_weight, standard_atomic_weight_table),
    (is_stable, is_stable_table),
    (particle_mass, particle_mass_table),
    (integer_charge, integer_charge_table),
    (electric_charge, electric_charge_table),
    (half_life, half_life_table),
]

all_tests = []

for func, table in tables_and_functions:
    for inputs in table:
        inputs.insert(0, func)
        if len(inputs) == 3:
            inputs.insert(2, {})
    all_tests += table

# Set up tests for a variety of atomic functions to make sure that bad
# inputs lead to the expected errors.

atomic_TypeError_funcs_table = [
    atomic_symbol,
    isotope_symbol,
    atomic_number,
    is_stable,
    half_life,
    mass_number,
    element_name,
    standard_atomic_weight,
    nuclear_binding_energy,
    nuclear_reaction_energy,
]

atomic_TypeError_badargs = [1.1, {"cats": "bats"}, 1 + 1j]

atomic_ParticleErrors_funcs_table = [
    atomic_symbol,
    isotope_symbol,
    atomic_number,
    is_stable,
    half_life,
    mass_number,
    element_name,
    standard_atomic_weight,
    particle_mass,
    known_isotopes,
    stable_isotopes,
    common_isotopes,
    isotopic_abundance,
    integer_charge,
    electric_charge,
]

atomic_ParticleError_badargs = [
    -1,
    119,
    "grumblemuffins",
    "H-0",
    "Og-294b",
    "H-9343610",
    "Fe 2+4",
    "Fe+24",
    "Fe +59",
    "C++++++++++++++++",
    "C-++++",
    "h",
    "d",
    "he",
    "au",
    "alpha 1+",
    "alpha-4",
]

metatable = [
    (atomic_TypeError_funcs_table, atomic_TypeError_badargs, TypeError),
    (
        atomic_ParticleErrors_funcs_table,
        atomic_ParticleError_badargs,
        InvalidParticleError,
    ),
]

for funcs, badargs, error in metatable:
    for func in funcs:
        for badarg in badargs:
            all_tests += [[func, badarg, error]]


@pytest.mark.parametrize("inputs", all_tests)
def test_atomic_functions(inputs):
    print(inputs)
    run_test(inputs)


# from test_nuclear.py
test_nuclear_table = [
    [nuclear_binding_energy, "p", {}, 0 * u.J],
    [nuclear_binding_energy, "n", {}, 0 * u.J],
    [nuclear_binding_energy, "p", {}, 0 * u.J],
    [nuclear_binding_energy, "H", {}, ParticleError],
    [nuclear_binding_energy, "He-99", {}, InvalidParticleError],
    [nuclear_binding_energy, "He", {"mass_numb": 99}, InvalidParticleError],
    [nuclear_binding_energy, 3.1415926535j, {}, TypeError],
    [mass_energy, "e-", {}, (const.m_e * const.c ** 2).to(u.J)],
    [mass_energy, "p+", {}, (const.m_p * const.c ** 2).to(u.J)],
    [mass_energy, "H-1", {}, (const.m_p * const.c ** 2).to(u.J)],
    [mass_energy, "H-1 0+", {}, (const.m_p * const.c ** 2).to(u.J)],
    [mass_energy, "n", {}, (const.m_n * const.c ** 2).to(u.J)],
    [nuclear_reaction_energy, (), {"reactants": ["n"], "products": 3}, TypeError],
    [
        nuclear_reaction_energy,
        (),
        {"reactants": ["n"], "products": ["He-4"]},
        ParticleError,
    ],
    [
        nuclear_reaction_energy,
        (),
        {"reactants": ["h"], "products": ["H-1"]},
        ParticleError,
    ],
    [
        nuclear_reaction_energy,
        (),
        {"reactants": ["e-", "n"], "products": ["p+"]},
        ParticleError,
    ],
    [
        nuclear_reaction_energy,
        (),
        {"reactants": ["e+", "n"], "products": ["p-"]},
        ParticleError,
    ],
    [
        nuclear_reaction_energy,
        (),
        {"reactants": ["ksdf"], "products": ["H-3"]},
        ParticleError,
    ],
    [
        nuclear_reaction_energy,
        (),
        {"reactants": ["H"], "products": ["H-1"]},
        ParticleError,
    ],
    [
        nuclear_reaction_energy,
        (),
        {"reactants": ["p"], "products": ["n", "n", "e-"]},
        ParticleError,
    ],
    [nuclear_reaction_energy, "H + H --> H", {}, ParticleError],
    [nuclear_reaction_energy, "H + H", {}, ParticleError],
    [nuclear_reaction_energy, 1, {}, TypeError],
    [nuclear_reaction_energy, "H-1 + H-1 --> H-1", {}, ParticleError],
    [nuclear_reaction_energy, "p --> n", {}, ParticleError],
    [
        nuclear_reaction_energy,
        "p --> p",
        {"reactants": "p", "products": "p"},
        ParticleError,
    ],
]


@pytest.mark.parametrize("test_inputs", test_nuclear_table)
def test_nuclear(test_inputs):
    run_test(*test_inputs, rtol=1e-3)

