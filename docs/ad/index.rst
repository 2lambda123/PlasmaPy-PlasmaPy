.. include:: ad_attention.inc

.. _ad:

======================
Analyses & Diagnostics
======================

Analyses and diagnostics go hand-in-hand, but have subtle differences.  Thus,
PlasmaPy gives each their own sub-packages, `plasmapy.analysis` and
`plasmapy.diagnostics` respectively.

Think of the `plasmapy.analysis` as your toolbox.  It has all the tools
(functionality) you need to analyze your data.  Functionality is built around
`numpy` arrays and each function has a well-defined, focused task.  For example,
:func:`numpy.fft.fft` does one specific task, compute the one-dimensional
discrete Fourier Transform.  Similarly,
:func:`plasmapy.analysis.swept_langmuir.find_floating_potential` only finds the
floating potential for a given langmuir trace.  It does not have smoothing.
It does not do any filtering.  It does not do any signal conditioning.  It has a
singular task to find the floating potential of a single langmuir trace.

Diagnostics on the other-hand have a much broader scope and leverage the tools
defined in `plasmapy.analysis` to give a more integrated user experience when
analyzing data.

----

.. toctree::
   :maxdepth: 2
   :caption: The Packages

   Analyses <analysis/index>
   Diagnostics <diagnostics/index>
