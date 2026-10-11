"""The Rename Anything mod generator, split into feature slices.

``tools/gen.py`` is the command-line entry point; this package holds the code.
The layout follows the features of the mod rather than the output files, so a
change to one feature (for example the Cities tab) touches one module:

* :mod:`modgen.common`: paths, game limits and names shared by every slice.
* :mod:`modgen.charset`: the character code table of the name buffers.
* :mod:`modgen.script`, :mod:`modgen.gui`: small builders for Paradox script
  (``defined_text`` and friends) and for ``.gui`` elements.
* :mod:`modgen.output`: where generated files go (the ``OutputSink`` protocol).
* :mod:`modgen.ui_strings`: the English and Polish UI string catalogue.
* :mod:`modgen.features`: one module per feature: the main window frame,
  the Country, Characters, States and Cities tabs, the input window with its
  on-screen keyboard, the name buffers, the rename cooldown, the in-place
  editor copy, the localisation tables and the textures.
* :mod:`modgen.build`: assembles the slices into the output files in the
  order the files have always had, so the output stays byte-identical.
"""
