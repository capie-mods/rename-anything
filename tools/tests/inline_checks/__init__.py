"""The in-place editor test, split by what it checks.

``tools/tests/check_inline_editor.py`` is the entry point; it puts ``tools/`` on
``sys.path`` (for :mod:`modgen` and :mod:`rncommon`) and runs the modules below
in a fixed order:

* :mod:`inline_checks.constants`: paths, layout limits and error codes.
* :mod:`inline_checks.fixtures`: the borrowed ApplyVM and parser
  (``probes/rn_inline_pair_apply_source/check.py``) and the native alphabet.
* :mod:`inline_checks.tree`: parse-tree helpers and source loaders.
* :mod:`inline_checks.generated`: the generated ``mod/`` files.
* :mod:`inline_checks.structure` and :mod:`inline_checks.geometry`: the source
  contract and the window layout.
* :mod:`inline_checks.vm_cases`: limited execution of the real Apply paths.
* :mod:`inline_checks.mutations`: broken copies the structural checks must reject.
* :mod:`inline_checks.loading`: loading the source into parse trees and the VM context.
"""
