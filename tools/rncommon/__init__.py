"""Helpers shared by the offline tools in ``tools/``.

The package is imported by ``tools/gen.py`` (through :mod:`modgen`),
``tools/check.py``, ``tools/audit-debug-bridge.py`` and the tests in
``tools/tests``. Each of those scripts is started as ``python tools/<name>.py``,
so ``tools/`` is the first entry of ``sys.path`` and ``import rncommon`` works
without installing anything.

Modules:

* :mod:`rncommon.game_data`: read-only access to a vanilla HOI4 installation
  (state history, English victory point keys, interface sprites) behind the
  :class:`~rncommon.game_data.GameData` protocol.
* :mod:`rncommon.loc_files`: the localisation line format and a table reader.
* :mod:`rncommon.hashing`: SHA-256 digests of files in the forms the reports use.
"""
