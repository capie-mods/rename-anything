# Native input / party QA probe

Unloaded development probe, excluded from `mod/` and any release. Activation must
wait for a full game exit. The current native DLL does **not** implement its input
bridge, and this probe does not claim an operational in-place editor.

When active in a POL campaign, opening the Politics panel attaches a small test
window to its right. It contains a real vanilla `editBoxType` named
`rn_native_edit_unique`, initially supplied with fixed text `Zażółć QA`.
This fixed value is a constructor/text-layout control; it is not evidence of
typing or of reading a player's edit.

The first button logs three proposed command temporary variables. Until a
verified bridge supplies them, their values do not represent the editor text.
It changes no name. The second button deliberately tests `set_party_name` on
POL's neutral ruling party, using two literal strings without matching loc keys.
Readback labels use `GetRulingParty` and `GetRulingPartyLong`. This button requires
POL/neutrality and is restricted to a disposable own QA save.

Required evidence: constructor/type/name identity; focus and actual typing;
readout before and after editing; validated normal command transport; literal
party short/long display in native Politics and tooltips; own save/full restart/load
without repeat Apply; matched error-log deltas. None is established by these files.

The unwired `rn_native_probe_apply_input` candidate in `common/scripted_effects/`
requires a fresh normal command with 34 temporary variables: `rn_native_ok`,
`rn_native_len`, and `rn_native_0` through `rn_native_31`. It validates the complete
length, active integer CHARS codes and zero padding before copying to the existing
`rn_buf` and calling the existing guarded `rn_apply_input`. Error payloads keep
the buffer and target intact. The explicit engine namespace is `temp_var:`.
No current GUI button calls this candidate. Parser/runtime, command freshness
and actual Apply remain separate checks after the observational field test.

The coordinator must archive own QA saves before any overwrite, keep user saves
untouched, record descriptor/config hashes on activation, and restore the original
playset plus remove only the descriptor created for this probe after testing.
