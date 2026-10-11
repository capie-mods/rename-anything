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
