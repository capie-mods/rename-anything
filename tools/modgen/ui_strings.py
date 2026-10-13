"""The English and Polish UI strings of the legacy editor.

This is the one translation catalogue of ``tools/gen.py``: every user-visible
string of the Rename window, the input window and the state view panel. It is
kept in one module instead of being split across the feature slices because
translators and the wording test (``tools/tests/check_inline_editor.py``,
``check_voice``) read it as one table, and because the order of the entries is
the order of the lines in ``rename_anything_l_<lang>.yml``.

Wording follows ``docs/design/DESIGN-SYSTEM.md`` (Voice and Tone): no dashes,
no internal words. ``{days}`` is replaced by the cooldown length when the file
is written.
"""

from __future__ import annotations

from modgen.common import MAXLEN, slots_expr

UI: dict[str, tuple[str, str]] = {
    # Each value holds the English text first, then the Polish text. Wording follows
    # docs/design/DESIGN-SYSTEM.md (Voice and Tone): no dashes, no internal words.
    "RN_MAIN_TITLE": ("Rename", "Zmiana nazw"),
    "RN_TAB_1": ("Country", "Kraj"),
    "RN_TAB_2": ("Characters", "Postacie"),
    "RN_TAB_3": ("States", "Stany"),
    "RN_TAB_4": ("Cities", "Miasta"),
    "RN_CUR_NAME": ("§LCurrent name:§! [ROOT.GetName]", "§LObecna nazwa:§! [ROOT.GetName]"),
    "RN_CUR_ADJ": ("§LAdjective:§! [ROOT.GetAdjective]", "§LPrzymiotnik:§! [ROOT.GetAdjective]"),
    "RN_CUR_LEADER": ("§LLeader:§! [ROOT.GetLeader]", "§LPrzywódca:§! [ROOT.GetLeader]"),
    "RN_BTN_RENAME": ("Rename", "Zmień"),
    "RN_BTN_RESET": ("Reset", "Przywróć"),
    "RN_BTN_CITIES": ("Cities", "Miasta"),
    "RN_BTN_TYPE": ("Type...", "Wpisz..."),
    "RN_COUNTRY_HDR": ("Country name and adjective", "Nazwa i przymiotnik kraju"),
    "RN_COUNTRY_STATUS": ("[ROOT.RN_CountryStatus]", "[ROOT.RN_CountryStatus]"),
    "RN_CNAME_LINE": ("§LName:§! " + slots_expr("N"), "§LNazwa:§! " + slots_expr("N")),
    "RN_CADJ_LINE": (
        "§LAdjective:§! " + slots_expr("J"),
        "§LPrzymiotnik:§! " + slots_expr("J"),
    ),
    "RN_BTN_COUNTRY_APPLY": ("Apply", "Zastosuj"),
    "RN_BTN_COUNTRY_RESET": ("Original name", "Przywróć oryginalną nazwę"),
    "RN_COUNTRY_APPLY_TT": (
        (
            "Rename Anything needs CAPIE, which is not loaded. Start the game with the "
            "CAPIE launcher. Nothing was changed."
        ),
        (
            "Rename Anything wymaga CAPIE, które nie jest załadowane. Uruchom grę przez "
            "launcher CAPIE. Nic nie zmieniono."
        ),
    ),
    "RN_COUNTRY_RESET_TT": (
        (
            "Removes the name you gave. The country shows the game's name again (its current "
            "cosmetic name, if any). Flag and colour do not change."
        ),
        (
            "Usuwa nadaną nazwę. Kraj wraca do nazwy z gry (bieżącej nazwy kosmetycznej, jeśli "
            "jest). Flaga i kolor się nie zmieniają."
        ),
    ),
    "RN_COUNTRY_NOTE": (
        (
            "Custom country names need CAPIE in every game session. Start the game with the "
            "CAPIE launcher. Without it the country shows its original name."
        ),
        (
            "Własna nazwa kraju wymaga CAPIE w każdej sesji gry. Uruchom grę przez launcher "
            "CAPIE. Bez niego kraj ma swoją pierwotną nazwę."
        ),
    ),
    "RN_COUNTRY_STATUS_READY": (
        "Fill in both fields. Needs CAPIE.",
        "Wypełnij oba pola. Wymaga CAPIE.",
    ),
    "RN_COUNTRY_STATUS_STORED": (
        "Custom text stored. Check the current name above.",
        "Tekst zapisany. Sprawdź obecną nazwę powyżej.",
    ),
    # Fallback text; the native library overrides this key while it is loaded.
    # Kept for compatibility: older country DLLs override only this bare key.
    "RN_PLUGIN_STATUS": (
        "CAPIE missing: Rename Anything needs it",
        "Brak CAPIE: wymaga go Rename Anything",
    ),
    # CAPIE status (capie_core.dll): the DLL overrides the BARE key with the English text,
    # so the language is chosen here, not by redefining the bare key: Polish references the
    # _PL key, every other language the _EN key. The values below are the fallbacks shown
    # when the DLL is not loaded. Ship together with capie_core.dll (older DLLs do not
    # override _EN/_PL, so they would show the "missing" fallback).
    "RN_PLUGIN_STATUS_EN": (
        "CAPIE missing: Rename Anything needs it",
        "CAPIE missing: Rename Anything needs it",
    ),
    "RN_PLUGIN_STATUS_PL": (
        "Brak CAPIE: wymaga go Rename Anything",
        "Brak CAPIE: wymaga go Rename Anything",
    ),
    "RN_COUNTRY_PLUGIN": ("$RN_PLUGIN_STATUS_EN$", "$RN_PLUGIN_STATUS_PL$"),
    "RN_PAGE": (
        "Page [?ROOT.rn_cpage_disp|0] / [?ROOT.rn_cpages|0]",
        "Strona [?ROOT.rn_cpage_disp|0] / [?ROOT.rn_cpages|0]",
    ),
    "RN_SPAGE": (
        "Page [?ROOT.rn_spage_disp|0] / [?ROOT.rn_spages|0]",
        "Strona [?ROOT.rn_spage_disp|0] / [?ROOT.rn_spages|0]",
    ),
    "RN_BTN_PREV": ("< Prev", "< Wstecz"),
    "RN_BTN_NEXT": ("Next >", "Dalej >"),
    "RN_CHAR_NAME": ("[?rn_row_character.GetName]", "[?rn_row_character.GetName]"),
    # Tooltips of the role icons in the Characters list (see characters.CHAR_ROLES).
    "RN_CHAR_ROLE_LEADER": ("Country leader", "Przywódca państwa"),
    "RN_CHAR_ROLE_ARMY": ("General", "Generał"),
    "RN_CHAR_ROLE_NAVY": ("Admiral", "Admirał"),
    "RN_CHAR_ROLE_ADVISER": ("Adviser", "Doradca"),
    "RN_STATE_NAME": ("[This.GetName]", "[This.GetName]"),
    "RN_SEL_STATE_LBL": ("State:", "Stan:"),
    "RN_CITIES_HINT": (
        "Pick a state with 'Cities' in the States tab or in the state view on the map.",
        "Wybierz stan przyciskiem „Miasta” w zakładce Stany albo w widoku stanu na mapie.",
    ),
    "RN_NO_CITIES": (
        "This state has no victory points.",
        "Ten stan nie ma punktów zwycięstwa (miast).",
    ),
    "RN_CITIES_NOTE": (
        (
            "A city renamed here shows its original name and the new one in brackets. "
            "Names changed before this version show only the original name."
        ),
        (
            "Miasto, którego nazwę zmieniono tutaj, ma pierwotną nazwę i nową w nawiasie. "
            "Nazwy zmienione przed tą wersją pokazują tylko nazwę pierwotną."
        ),
    ),
    "RN_CLOSE_TT": ("Close", "Zamknij"),
    # input window
    "RN_INPUT_TITLE": (
        "Rename: [ROOT.RN_TargetTypeLabel]",
        "Zmiana nazwy: [ROOT.RN_TargetTypeLabel]",
    ),
    "RN_TTYPE_0": ("-", "-"),
    "RN_TTYPE_1": ("character", "postać"),
    "RN_TTYPE_2": ("state", "stan"),
    "RN_TTYPE_3": ("city", "miasto"),
    "RN_TTYPE_4": ("country name", "nazwa kraju"),
    "RN_TTYPE_5": ("country adjective", "przymiotnik kraju"),
    "RN_TARGET_PROV": ("§Y[ROOT.RN_TProvName]§!", "§Y[ROOT.RN_TProvName]§!"),
    "RN_TARGET_COUNTRY": ("§Y[ROOT.GetName]§!", "§Y[ROOT.GetName]§!"),
    "RN_TARGET_ENTRY": ("§Y[This.GetName]§!", "§Y[This.GetName]§!"),
    "RN_TARGET_DISPLAY": ("§Y[?rn_header_target.GetName]§!", "§Y[?rn_header_target.GetName]§!"),
    "RN_FIELD_TEXT": (slots_expr("B") + "§Y|§!", slots_expr("B") + "§Y|§!"),
    "RN_FIELD_COUNT": (f"[?ROOT.rn_len|0]/{MAXLEN}", f"[?ROOT.rn_len|0]/{MAXLEN}"),
    "RN_KEY_SPACE": ("Space", "Spacja"),
    "RN_KEY_BACKSPACE": ("Backspace", "Backspace"),
    "RN_KEY_CLEAR": ("Clear", "Wyczyść"),
    "RN_KEY_CAPS_OFF": ("abc", "abc"),
    "RN_KEY_CAPS_ON": ("ABC", "ABC"),
    "RN_KEY_CAPS": ("Caps: [ROOT.RN_CapsLabel]", "Wielkie: [ROOT.RN_CapsLabel]"),
    "RN_BTN_CANCEL": ("Cancel", "Anuluj"),
    "RN_BTN_APPLY": ("Apply", "Zastosuj"),
    "RN_INPUT_HINT": (
        (
            "Type letters, Shift+letter, digits, - and .; Backspace deletes, Enter applies. "
            "Game hotkeys also remain active. Polish letters and ' via buttons. Max 32 characters."
        ),
        (
            "Pisz litery, Shift+litera, cyfry, - i .; Backspace kasuje, Enter zatwierdza. "
            "Skróty gry pozostają aktywne. Polskie litery i ' przyciskami. Maks. 32 znaki."
        ),
    ),
    "RN_APPLY_TT": ("Apply the typed name.", "Zatwierdź wpisaną nazwę."),
    # state view panel
    "RN_SV_TITLE": ("Rename", "Zmiana nazw"),
    "RN_SV_RENAME": ("Rename state", "Zmień nazwę"),
    "RN_SV_CITIES": ("Cities", "Miasta"),
    "RN_SV_RESET": ("Reset", "Przywróć"),
    # rename cooldown (states and cities); {days} is replaced by COOLDOWN_DAYS in ui_loc
    "RN_CD_STATE_TT": ("[ROOT.RN_CD_STATE_LEFT]", "[ROOT.RN_CD_STATE_LEFT]"),
    "RN_CD_VP_TT": ("[ROOT.RN_CD_VP_LEFT]", "[ROOT.RN_CD_VP_LEFT]"),
    "RN_CD_STATE_READY": (
        "You can rename one state every {days} days.",
        "Nazwę stanu można zmieniać raz na {days} dni.",
    ),
    "RN_CD_VP_READY": (
        "You can rename one city every {days} days.",
        "Nazwę miasta można zmieniać raz na {days} dni.",
    ),
}
"""UI localisation key to (English text, Polish text); other languages use English."""
