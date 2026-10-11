"""Feature slices of the generator; each module owns one part of the mod.

A slice returns text fragments (scripted localisation blocks, effects, scripted
GUI blocks, ``.gui`` elements, localisation lines). :mod:`modgen.build` decides
which fragments go into which file and in which order.
"""
