> **WYCOFANY (integracja z mod/, 2026-10-11).** Ten fixture został przeniesiony do generatora:
> źródło `tools/inline_editor/`, wynik w `mod/` (`tools/gen.py`), testy w
> `tools/tests/check_inline_editor.py`. Globalny przycisk `rn_entry_gui` usunięto w generatorze.
> **Nie ładuj tego katalogu razem z `mod/`** — te same nazwy modeli, efektów i kluczy
> (oraz ten sam plik SG w layout) dałyby duplikaty albo cofnęłyby zmiany generatora.
> Zostaje w repo jako historia QA.

# Nieaktywny kandydat wejścia do edytora

Użytkownik zgłosił 2026-10-11, że globalny przycisk „Zmień nazwy” zasłania portret
lidera i okno decyzji. Ten kandydat ukrywa wyłącznie `rn_entry_gui`. Pozostałe
funkcje dawnego edytora otwiera bezpłatna, powtarzalna decyzja w zwykłej kategorii
Rename Anything. Przyciski edycji przy nazwie kraju/lidera/partii i istniejące
przyciski w kontekście wybranego stanu pozostają osobnymi ścieżkami.

Plik `common/scripted_guis/rename_anything_scripted_gui.txt` celowo przesłania
dokładnie ten sam plik z dev moda. Jedyna różnica to `rn_entry_gui.visible`:
`always=yes` → `always=no`. Nie należy ładować obu definicji pod różnymi ścieżkami.
Nie zmieniono jeszcze głównego moda ani generatora. Po QA poprawka musi trafić
do generatora wraz z decyzją i lokalizacją; ten katalog nie jest wydaniem.

Decyzja nie wydaje punktów, nie nadaje premii, nie dotyka zapisanych nazw i nie
zamyka innego draftu. Availability i actual effect powtarzają guard zamkniętych
edytorów. Korzysta z istniejącego `rn_open_main` we własnym kontekście kraju.
Ostateczna obsługa scope i kolejki decyzji wymaga testu silnika; MP jest odłożony.

Source-only: brak deskryptora w profilu, aktywacji, DLL, zmiany konfiguracji i QA.
Przed wdrożeniem: świeży proces z dev modem oraz tym kandydatem; portret i pełny
panel decyzji bez pływającego przycisku, otwarcie/Close/reopen decyzją na pauzie,
brak kosztu/cooldownu, block podczas draftu, nadal działające ścieżki stanu/miast,
PL/EN i porównanie error.log z bazą tego samego procesu. Niezależny review potrzebny.

Poprawka Claude script/UI 2026-10-11 (po review 915A493C): ikona decyzji to
`generic_political_discourse`, bo vanilla 1.19.3 nie definiuje
`GFX_decision_generic_political_actions` (istnieje tylko sprite kategorii). Pięć
flag w `available` jest w jednym `custom_trigger_tooltip` z kluczem
`rn_open_name_editor_blocked_tt` (EN/PL), zamiast pięciu surowych nazw flag.
Guard w `complete_effect` bez zmian. Statyczny check:
`docs/evidence/session-20261011/claude-script-ui/layout_check.py`.

Iteracja 3 (product): ten sam override `rn_entry_gui` jest teraz także w
`probes/rn_inline_editor_product_qa` (bajtowo identyczny plik, `dependencies` na dev mod).
Nie ładuj tego fixture razem z product: dwa mody nadpisywałyby tę samą ścieżkę.

