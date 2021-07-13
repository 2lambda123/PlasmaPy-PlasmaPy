"""
This module contains the functionality used to define the :rst:dir:`automodsumm`
directive and its :ref:`supporting configuration values <automodsumm-confvals>`.

.. contents:: Content
   :local:

`automodsumm` Directive
-----------------------

.. rst:directive:: automodsumm

    The :rst:dir:`automodsumm` directive is a wrapper on Sphinx's
    :rst:dir:`autosummary` directive and, as such, all the options for
    :rst:dir:`autosummary` still work.  The difference, where :rst:dir:`autosummary`
    requires a list of all the objects to document, :rst:dir:`automodsumm`
    only requires the module name and then it will inspect the module to find
    all the objects to be documented according to the listed options.

    The module inspection will respect the ``__all__`` dunder if defined; otherwise,
    it will inspect all objects of the module.  The inspection will only gather
    direct sub-modules and ignore any 3rd party objects, unless listed in
    ``__all__``.

    The behavior of :rst:dir:`automodsumm` can additionally be set with the
    :ref:`configuration values described below <automodsumm-confvals>`.

    .. rst:directive:option:: groups

        When a module is inspected all the identified objects are categorized into
        groups.  The built-in groups are:

        +----------------+-------------------------------------------------------------+
        | **modules**    | Direct sub-packages and modules.                            |
        +----------------+-------------------------------------------------------------+
        | **classes**    | Python classes. (excluding **exceptions** and **warnings**) |
        +----------------+-------------------------------------------------------------+
        | **exceptions** | Classes that inherit from `BaseException`. (excluding       |
        |                | **warnings**)                                               |
        +----------------+-------------------------------------------------------------+
        | **warnings**   | Classes that inherit from `Warning`.                        |
        +----------------+-------------------------------------------------------------+
        | **functions**  | Objects that satisfy :func:`inspect.isroutine`.             |
        +----------------+-------------------------------------------------------------+
        | **variables**  | All other objects.                                          |
        +----------------+-------------------------------------------------------------+

        In addition to the built-in groups, groups defined in
        :confval:`automodapi_custom_groups` will be categorized.  When objects are
        collected and grouped the **modules** will be done first, followed by any
        custom group, and, finally, the built-in groups.  By default, **all** groups
        will be included in the generated table.

        Using the `plasmapy_sphinx.automodsumm.core` module as an example, the
        :ref:`module's API <automodsumm-api>` shows it is made of classes
        and functions.  So the following yields,

        .. code-block:: rst

            .. automodsumm:: plasmapy_sphinx.automodsumm.core

            or

            .. automodsumm:: plasmapy_sphinx.automodsumm.core
               :groups: all

        .. automodsumm:: plasmapy_sphinx.automodsumm.core

        However, if you only want to collect classes then one could do

        .. code-block:: rst

            .. automodsumm:: plasmapy_sphinx.automodsumm.core
               :groups: classes

        .. automodsumm:: plasmapy_sphinx.automodsumm.core
           :groups: classes

        If you want to include multiple groups, then specify all groups as a
        comma separated list.

        .. code-block:: rst

            .. automodsumm:: plasmapy_sphinx.automodsumm.core
               :groups: classes, functions

    .. rst:directive:option:: exclude-groups

        This option behaves just like :rst:dir:`automodsumm:groups` except
        you are selectively excluding groups for the generated table.  Using the
        same example as before, a table of just **classes** can be generated by
        doing

        .. code-block:: rst

            .. automodsumm:: plasmapy_sphinx.automodsumm.core
               :exclude-groups: functions

        .. automodsumm:: plasmapy_sphinx.automodsumm.core
           :exclude-groups: functions

    .. rst:directive:option:: skip

        This option allows you to skip (exclude) selected objects from the
        generated table.  The argument is given as a comma separated list of
        the object's short name.  Continuing with the example from above, lets
        skip `~plasmapy_sphinx.automodsumm.core.AutomodsummOptions` and
        `~plasmapy_sphinx.automodsumm.core.setup` from the table.

        .. code-block:: rst

            .. automodsumm:: plasmapy_sphinx.automodsumm.core
               :skip: AutomodsummOptions, setup

        .. automodsumm:: plasmapy_sphinx.automodsumm.core
           :skip: AutomodsummOptions, setup

    .. rst:directive:option:: toctree

        If you want the :rst:dir:`automodsumm` table to serve as a :rst:dir:`toctree`,
        then specify this option with a directory path ``DIRNAME`` with respect to
        the location of your ``conf.py`` file.

        .. code-block:: rst

            .. automodsumm:: plasmapy_sphinx.autodoc.automodapi
                :toctree: DIRNAME

        This will signal `sphinx-autogen
        <https://www.sphinx-doc.org/en/master/man/sphinx-autogen.html>`_
        to generate stub files for the objects in the table and place them in
        the directory named by ``DIRNAME``.  This behavior respects the
        configuration value :confval:`autosummary_generate`.  Additionally,
        :rst:dir:`automodsumm` will not generate stub files for entry that
        falls into the **modules** group (see the :rst:dir:`automodsumm:groups`
        option below), unless :confval:`automodapi_generate_module_stub_files`
        is set ``True``.

.. _automodsumm-confvals:

`automodsumm` Configuration Values
----------------------------------

A configuration value is a variable that con be defined in ``conf.py`` to configure
the default behavior of related `sphinx` directives.  The configuration values
below relate to the behavior of the :rst:dir:`automodsumm` directive.

.. confval:: automodapi_custom_groups

    Configuration value used to define custom groups which are used by
    :rst:dir:`automodapi` and :rst:dir:`automodsumm` when sorting the discovered
    objects of an inspected module.  An example custom group definition looks like

    .. code-block:: python

        automodapi_custom_group = {
            "aliases": {
                "title": "Aliases",
                "description": "Aliases are ...",
                "dunder": "__aliases__",
            }
        }

    where the top-level key (``"aliases"``) is the group name used in the
    :rst:dir:`automodsumm:groups` option, ``"title"`` defines the title
    text of the group heading used by :rst:dir:`automodapi`, ``"description"``
    defines a brief description that will be placed after the title (item is
    optional and can be omitted) and ``"dunder"`` defines the name of a dunder
    variable (similar ``__all__``) in the module.  This dunder variable is
    defined at the top of the module being documented and defines a list of
    object names just like ``__all__``.  The :rst:dir:`automodapi` and
    :rst:dir:`automodsumm` directives will used this defined dunder to identify
    the objects associated with the custom group.  Using
    `plasmapy.formulary.parameters` as an example, the **aliases** group can
    now be collected and displayed like

    .. code-block:: rst

        .. automodsumm:: plasmapy.formulary.parameters
           :groups: aliases

    .. automodsumm:: plasmapy.formulary.parameters
           :groups: aliases

.. confval:: automodapi_generate_module_stub_files

    (Default `False`)  By default :rst:dir:`automodsumm` will not generated stub files
    for the **modules** group, even when the `sphinx` configuration value
    `autosummary_generate
    <https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html?
    highlight=autosummary_generate#confval-autosummary_generate>`_
    is set `True`.  Setting this configure variable to `True` will cause stub
    files to be generated for the **modules** group.

.. confval:: autosummary_generate

    Same as the :rst:dir:`autosummary` configuration value `autosummary_generate
    <https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html?
    highlight=autosummary_generate#confval-autosummary_generate>`_.
"""
__all__ = [
    "Automodsumm",
    "AutomodsummOptions",
    "option_str_list",
    "setup",
]

import os

from importlib import import_module
from sphinx.ext.autosummary import Autosummary
from sphinx.util import logging
from typing import Any, Callable, Dict, List, Tuple, Union

from ..automodsumm.generate import GenDocsFromAutomodsumm
from ..utils import default_grouping_info, find_mod_objs, get_custom_grouping_info

if False:
    # noqa
    # for annotation, does not need real import
    from docutils.nodes import Node
    from docutils.statemachine import StringList
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment

logger = logging.getLogger(__name__)


def option_str_list(argument):
    """
    An option validator for parsing a comma-separated option argument.  Similar to
    the validators found in `docutils.parsers.rst.directives`.
    """
    if argument is None:
        raise ValueError("argument required but none supplied")
    else:
        return [s.strip() for s in argument.split(",")]


class AutomodsummOptions:
    """
    Class for advanced conditioning and manipulation of option arguments for
    `plasmapy_sphinx.automodsumm.core.Automodsumm`.
    """

    option_spec = {
        **Autosummary.option_spec,
        "groups": option_str_list,
        "exclude-groups": option_str_list,
        "skip": option_str_list,
    }
    """
    Mapping of option names to validator functions. (see
    :attr:`docutils.parsers.rst.Directive.option_spec`)
    """

    _default_grouping_info = default_grouping_info.copy()

    logger = logger
    """
    Instance of the `~sphinx.util.logging.SphinxLoggerAdapter` for report during
    builds.
    """

    def __init__(
        self,
        app: "Sphinx",
        modname: str,
        options: Dict[str, Any],
        docname: str = None,
        _warn: Callable = None,
    ):
        """
        Parameters
        ----------
        app : `~sphinx.application.Sphinx`
            Instance of the sphinx application.

        modname : `str`
            Name of the module given in the :rst:dir:`automodsumm` directive.  This
            is the module to be inspected and have it's objects grouped.

        options : Dict[str, Any]
            Dictionary of options given for the :rst:dir:`automodsumm` directive
            declaration.

        docname : str
            Name of the document/file where the :rst:dir:`automodsumm` direction
            was declared.

        _warn : Callable
            Instance of a `sphinx.util.logging.SphinxLoggerAdapter.warning` for
            reporting warning level messages during a build.
        """

        self._app = app
        self._modname = modname
        self._options = options.copy()
        self._docname = docname
        self._warn = _warn if _warn is not None else self.logger.warning

        self.toctree = {
            "original": None,
            "rel_to_doc": None,
            "abspath": None,
        }  # type: Dict[str, Union[str, None]]

        self.condition_options()

    @property
    def app(self) -> "Sphinx":
        """Instance of the sphinx application."""
        return self._app

    @property
    def modname(self) -> str:
        """Name of the module given to :rst:dir:`automodsumm`."""
        return self._modname

    @property
    def options(self) -> Dict[str, Any]:
        """Copy of the options given to :rst:dir:`automodsumm`."""
        return self._options

    @property
    def docname(self) -> str:
        """Name of the document where :rst:dir:`automodsumm` was declared."""
        return self._docname

    @property
    def warn(self) -> Callable:
        """
        Instance of a `sphinx.util.logging.SphinxLoggerAdapter.warning` for
        reporting warning level messages during a build.
        """
        return self._warn

    @property
    def pkg_or_module(self) -> str:
        """
        Is module specified by :attr:`modname` a package or module (i.e. `.py` file).
        Return ``"pkg"`` for a package and ``"module"`` for a `.py` file.
        """
        mod = import_module(self.modname)
        if mod.__package__ == mod.__name__:
            return "pkg"
        else:
            return "module"

    def condition_options(self):
        """
        Method for doing any additional conditioning of option arguments.
        Called during class instantiation."""
        self.condition_toctree_option()
        self.condition_group_options()

    def condition_toctree_option(self):
        """
        Additional conditioning of the option argument ``toctree``. (See
        :rst:dir:`automodsumm:toctree` for additional details.)
        """
        if "toctree" not in self.options:
            return

        if self.docname is None:
            doc_path = self.app.confdir
        else:
            doc_path = os.path.dirname(os.path.join(self.app.srcdir, self.docname))

        self.toctree["original"] = self.options["toctree"]
        self.toctree["abspath"] = os.path.abspath(
            os.path.join(self.app.confdir, self.options["toctree"]),
        )
        self.toctree["rel_to_doc"] = os.path.relpath(
            self.toctree["abspath"], doc_path
        ).replace(os.sep, "/")

        self.options["toctree"] = self.toctree["rel_to_doc"]

    def condition_group_options(self):
        """
        Additional conditioning of the option arguments ``groups`` and
        ``exclude-groups``.  (See :rst:dir:`automodsumm:groups` and
        :rst:dir:`automodsumm:exclude-groups` for additional details.)
        """
        allowed_args = self.groupings | {"all"}
        do_groups = self.groupings.copy()  # defaulting to all groups

        # groups option
        if "groups" in self.options:
            opt_args = set(self.options["groups"])

            unknown_args = opt_args - allowed_args
            if len(unknown_args) > 0:
                self.warn(
                    f"Option 'groups' has unrecognized arguments "
                    f"{unknown_args}. Ignoring."
                )
                opt_args = opt_args - unknown_args

            if "all" not in opt_args:
                do_groups = opt_args

        # exclude groupings
        if "exclude-groups" in self.options:
            opt_args = set(self.options["exclude-groups"])
            del self.options["exclude-groups"]
        else:
            opt_args = set()

        unknown_args = opt_args - allowed_args
        if len(unknown_args) > 0:
            self.warn(
                f"Option 'exclude-groups' has unrecognized arguments "
                f"{unknown_args}. Ignoring."
            )
            opt_args = opt_args - unknown_args
        elif "all" in opt_args:
            self.warn(
                f"Arguments of 'groups' and 'exclude-groups' results in no content."
            )
            self.options["groups"] = []
            return

        do_groups = do_groups - opt_args
        self.options["groups"] = list(do_groups)

    @property
    def mod_objs(self) -> Dict[str, Dict[str, Any]]:
        """
        Dictionary of the grouped objects found in the module named by :attr:`modname`.

        See Also
        --------
        plasmapy_sphinx.utils.find_mod_objs
        """
        return find_mod_objs(self.modname, app=self.app)

    @property
    def groupings(self) -> set:
        """Set of all the grouping names."""
        return set(self.grouping_info)

    @property
    def default_grouping_info(self) -> Dict[str, Dict[str, str]]:
        """
        Dictionary of the default group information.

        See Also
        --------
        plasmapy_sphinx.utils.default_grouping_info
        """
        return self._default_grouping_info.copy()

    @property
    def custom_grouping_info(self) -> Dict[str, Dict[str, str]]:
        """
        Dictionary of the custom group info.

        See Also
        --------
        plasmapy_sphinx.utils.get_custom_grouping_info
        """
        return get_custom_grouping_info(self.app)

    @property
    def grouping_info(self) -> Dict[str, Dict[str, str]]:
        """
        The combined grouping info of :attr:`default_grouping_info` and
        :attr:`custom_grouping_info`
        """
        grouping_info = self.default_grouping_info
        grouping_info.update(self.custom_grouping_info)
        return grouping_info

    @property
    def mod_objs_option_filtered(self) -> Dict[str, Dict[str, Any]]:
        """
        A filtered version of :attr:`mod_objs` according to the specifications
        given in :attr:`options` (i.e. those given to :rst:dir:`automodsumm`).
        """
        try:
            mod_objs = self.mod_objs
        except ImportError:
            mod_objs = {}
            self.warn(f"Could not import module {self.modname}")

        do_groups = set(self.options["groups"])

        if len(do_groups) == 0:
            return {}

        # remove excluded groups
        for group in list(mod_objs):
            if group not in do_groups:
                del mod_objs[group]

        # objects to skip
        skip_names = set()
        if "skip" in self.options:
            skip_names = set(self.options["skip"])

        # filter out skipped objects
        for group in list(mod_objs.keys()):

            names = mod_objs[group]["names"]
            qualnames = mod_objs[group]["qualnames"]
            objs = mod_objs[group]["objs"]

            names_filtered = []
            qualnames_filtered = []
            objs_filtered = []

            for name, qualname, obj in zip(names, qualnames, objs):
                if not (name in skip_names or qualname in skip_names):
                    names_filtered.append(name)
                    qualnames_filtered.append(qualname)
                    objs_filtered.append(obj)

            if len(names_filtered) == 0:
                del mod_objs[group]
                continue

            mod_objs[group] = {
                "names": names_filtered,
                "qualnames": qualnames_filtered,
                "objs": objs_filtered,
            }
        return mod_objs

    def generate_obj_list(self, exclude_modules: bool = False) -> List[str]:
        """
        Take :attr:`mod_objs_option_filtered` and generated a list of the fully
        qualified object names.  The list is sorted based on the casefolded
        short names of the objects.

        Parameters
        ----------
        exclude_modules : bool
            (Default `False`) Set `True` to exclude the qualified names related to
            objects sorted in the **modules** group.
        """

        mod_objs = self.mod_objs_option_filtered

        if not bool(mod_objs):
            return []

        gather_groups = set(mod_objs.keys())
        if exclude_modules:
            gather_groups.discard("modules")

        names = []
        qualnames = []
        for group in gather_groups:
            names.extend(mod_objs[group]["names"])
            qualnames.extend(mod_objs[group]["qualnames"])

        content = [
            qualname
            for name, qualname in sorted(
                zip(names, qualnames), key=lambda x: str.casefold(x[0])
            )
        ]

        return content


class Automodsumm(Autosummary):
    """The class that defines the :rst:dir:`automodsumm` directive."""

    required_arguments = 1
    optional_arguments = 0
    has_content = False
    option_spec = AutomodsummOptions.option_spec.copy()

    def run(self):
        """
        This method is called whenever the :rst:dir:`automodsumm` directive is found
        in a document.  It is used to do any further manipulation of the directive,
        its options, and its content to get the desired rendered outcome.
        """
        env = self.env
        modname = self.arguments[0]

        # for some reason, even though ``currentmodule`` is substituted in,
        # sphinx doesn't necessarily recognize this fact.  So we just force
        # it internally, and that seems to fix things
        env.temp_data["py:module"] = modname
        env.ref_context["py:module"] = modname

        nodelist = []

        # update toctree with relative path to file (not confdir)
        if "toctree" in self.options:
            self.options["toctree"] = self.option_processor().options["toctree"]

        # define additional content
        content = self.option_processor().generate_obj_list()
        for ii, modname in enumerate(content):
            if not modname.startswith("~"):
                content[ii] = "~" + modname
        self.content = content

        nodelist.extend(Autosummary.run(self))
        return nodelist

    def option_processor(self):
        """
        Instance of `~plasmapy_sphinx.automodsumm.core.Automodsumm` so further processing
        (beyond :attr:`option_spec`) of directive options can be performed.
        """
        processor = AutomodsummOptions(
            app=self.env.app,
            modname=self.arguments[0],
            options=self.options,
            docname=self.env.docname,
            _warn=self.warn,
        )
        return processor

    def get_items(self, names):
        try:
            self.bridge.genopt["imported-members"] = True
        except AttributeError:  # Sphinx < 4.0
            self.genopt["imported-members"] = True
        return Autosummary.get_items(self, names)

    @property
    def genopt(self):
        """.. deprecated:: Sphinx 2.0.0"""
        return super().genopt

    @property
    def env(self) -> "BuildEnvironment":
        """Reference to the :class:`~sphinx.environment.BuildEnvironment` object."""
        return super().env

    @property
    def config(self) -> "Config":
        """Reference to the :class:`~sphinx.config.Config` object."""
        return super().config

    @property
    def result(self) -> "StringList":
        """
        A `docutils.statemachine.StringList` representing the lines of the
        directive.
        """
        return super().result

    @property
    def warnings(self) -> List["Node"]:
        """.. deprecated:: Sphinx 2.0.0"""
        return super().warnings

    def debug(self, message):
        """``level=0`` :meth:`directive_error`"""
        return super().debug(message)

    def info(self, message):
        """``level=1`` :meth:`directive_error`"""
        return super().info(message)

    def warning(self, message):
        """``level=2`` :meth:`directive_error`"""
        return super().warning(message)

    def error(self, message):
        """``level=3`` :meth:`directive_error`"""
        return super().error(message)

    def severe(self, message):
        """``level=4`` :meth:`directive_error`"""
        return super().severe(message)

    def warn(self, msg: str) -> None:
        """.. deprecated:: Sphinx 2.0.0"""
        super(Automodsumm, self).warn(msg)

    def import_by_name(
        self, name: str, prefixes: List[str]
    ) -> Tuple[str, Any, Any, str]:
        """See :func:`sphinx.ext.autosummary.import_by_name`"""
        return super(Automodsumm, self).import_by_name(name, prefixes)


def setup(app: "Sphinx"):
    """Sphinx ``setup()`` function for the :rst:dir:`automodsumm` functionality."""

    app.setup_extension("sphinx.ext.autosummary")

    app.add_directive("automodsumm", Automodsumm)

    gendocs_from_automodsumm = GenDocsFromAutomodsumm()
    app.connect("builder-inited", gendocs_from_automodsumm)
    app.connect(
        "autodoc-skip-member",
        gendocs_from_automodsumm.event_handler__autodoc_skip_member,
    )

    app.add_config_value("automodapi_custom_groups", dict(), True)
    app.add_config_value("automodapi_generate_module_stub_files", False, True)

    return {"parallel_read_safe": True, "parallel_write_safe": True}
