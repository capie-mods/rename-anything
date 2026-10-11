> **WYCOFANY (integracja z mod/, 2026-10-11).** Ten fixture został przeniesiony do generatora:
> źródło `tools/inline_editor/`, wynik w `mod/` (`tools/gen.py`), testy w
> `tools/tests/check_inline_editor.py`. Globalny przycisk `rn_entry_gui` usunięto w generatorze.
> **Nie ładuj tego katalogu razem z `mod/`** — te same nazwy modeli, efektów i kluczy
> (oraz ten sam plik SG w layout) dałyby duplikaty albo cofnęłyby zmiany generatora.
> Zostaje w repo jako historia QA.

# Nieaktywny kandydat własnego edytora nazw

Ten katalog rozwija zamrożony `rn_inline_editor_apply_qa`. Nie został zarejestrowany
w launcherze ani włączony. Nie zawiera nowej DLL, builda, injectora ani producenta
syntetycznego tekstu. `descriptor.template` wymaga osobnego przygotowania przez root
po review; w tym zadaniu konfiguracja gry pozostaje nietknięta.

Kraj, przymiotnik i aktualny przywódca mogą być edytowane dla własnego kraju gracza,
bez testowego ograniczenia do Polski. Partia oznacza wyłącznie partię aktualnie
rządzącą w jednej z czterech bazowych grup: democratic, communism, fascism,
neutrality. Nie obsługujemy w tym kandydacie opozycji ani własnych grup ideologii.
`player_context` ustanawia kontekst lokalnego gracza; dodatkowe `tag = ROOT`
sprawdza zgodność CURRENT z ROOT. `is_ai = no` jest warunkiem dostępności UI,
sam tag ani ten warunek nie dowodzą uprawnień lokalnego gracza. Multiplayer
i edycja obcego kraju nie są tutaj zaakceptowane.

Pozostają dokładne trzy modele, pięć natywnych pól, nazwy carrierów i selektorów
bridge opisane w [native-contract.json](native-contract.json). Sufiks `neutrality`
w nazwach kontrolek/modelu partii jest zachowanym kluczem protokołu; nie ogranicza
nowego dispatchu do tej grupy. Transport ma nadal 35/69/70 rekordów, świeży
`rn_ip_cmd_epoch` oraz dla kraju świeży `rn_native_cap=1` z wersjonowanej capability.
Enabled nie zależy od tempów dostarczanych dopiero przez konstruktor komendy.
Enter, autofocus i zaznaczanie tekstu zależą od osobno testowanego wariantu native;
te źródła nie dodają ich obsługi.

Open partii wybiera jedną jawną grupę, przypina typed COUNTRY `THIS`, zapisuje
logiczną grupę 1/2/3/4 oraz zwiększa wspólną epokę. Te liczby nie są ID silnika.
Apply ponawia kompletny guard kontekstu, epoki, kraju i zgodności grupy z bieżącym
rządem przed walidacją całej pary oraz po niej. Dopiero wybrana zgodna gałąź
kopiuje oba bufory i wykonuje jeden `meta_effect` z literalnymi short/long oraz
stałą ideologią. Brak zgodności daje error 9, field 0, zachowując draft, flagę,
epokę, piny i bufory. Nie ma ścieżki częściowego zapisu poprawnego A przy błędnym B.
Walidacja przed zapisem nie zapewnia rollbacku w razie awarii samego silnika.

Zmiana rządu blokuje także prefill: nowe warunkowe scripted localisation zwraca
pusty tekst obu carrierów, gdy przypięty kraj/grupa przestały odpowiadać celowi.
Istniejący native decoder odrzuca pusty snapshot; nie dopisujemy fałszywej nazwy.
Wiersz etykiety pokazuje wtedy „Zmieniony cel: Anuluj”, a Cancel pozostaje dostępny.
Powrót rządu do tej samej grupy oznacza ponownie tę logiczną partię; nie przypinamy
historycznej instancji rządu. Po Cancel nowe Open przypina aktualny rząd.

Lider nadal pochodzi z generic `every_character`/`is_country_leader`; nie było
POL-specific character IDs do usunięcia. Nowy czysto tymczasowy guard sprawdza
own aktywnego lidera i typed singleton przed pełną walidacją oraz po niej.
Dopiero później odświeżany jest dotychczasowy roster owned/current i sprawdzana
jednoznaczność. Dotychczasowy literalny `set_character_name`, strict copy oraz
guard charakteru w scope loop pozostają. Żaden helper nie otwiera starego `rn_input`.
Legacy `rn_open`/`rn_input` blokują visible/Open/Apply; Cancel działa niezależnie.

Typografia kraju zmienia wyłącznie dwa fonty pól na `hoi_16mbs` oraz zamkniętą
etykietę na `Arial12`. Geometria pozostaje identyczna, w tym wysokość pola 16 px;
obcięcie tekstu wymaga QA. Fonty pochodzą z vanilla `core.gfx`: hoi_16mbs
1093–1111, Arial12 1733–1753. Rozmiar nazwy zasłoniętej pod polem nie jest
naprawiany lokalnym fałszywym odczytem ani automatycznym zamykaniem polityki.

Partia ma jeden ołówek 20×20 (scale 0.67) w prawym górnym rogu natywnego
ruling_party_info, lokalnie 228,310, obok nazwy ideologii rządzącej; tooltip pokazuje
nazwę partii rządzącej. (Wersja v1: pasek „Partia rządząca” 18,368 z ołówkiem 15 px —
PID36204: użytkownik ocenił go jako „ledwo widoczny”.) Otwarty editor 18,300 / 250×66
(do x268, przed pie chart x270; do y366, przed y383/y390) tymczasowo zakrywa emblemat
ideologii i ruling_party_info. Pola mają ramki `GFX_tiles_dark_area_cut_8` (vanilla
social.gfx, wzór social_view editbox_search): krótka nazwa `hoi_18` 176×20 (jak
`group_name` armii: hoi_18 135×23), długa `hoi_16mbs` 238×20; status `Arial12`
6,26 /238×14. (v1: 138×18 i 176×18 bez ramek — „malusieńkie”.)

Primary `interface/countrypoliticsview.gui`: ruling_party_info jest 88,305 /255×60
(95–126), elections kończy się na y366; pie chart zaczyna x270 (75–94).
Manage occupied/subjects/collaborations są na y390 (656–735), więc oba nowe
prostokąty partii kończą się przed nimi. Native informacje mogą wystawać poza
nasz frame; hit testing, warstwy, tooltips i czytelność wymagają zrzutu w grze.
Nie dodajemy hotspotu na samej nazwie ani nowych assetów. Lider ma launcher
152,270 /20×20 wewnątrz natywnej tabliczki leader_name i editor 18,262 /155×36.

Poprawka Claude script/UI 2026-10-11: `GFX_edit_designer_notes_button` i
`GFX_preset_button_save` to klatki 30×30 (DDS 120×30, 4 klatki); `size{}` na
buttonType nie zmniejszał ich w grze (zrzut run42556 #141: ołówek ~25 px nad
tekstem ideologii „Bez powiązań”, Zapisz nachodził na Anuluj). Sześć takich
przycisków ma `scale` zamiast `size`: lider i partia 0.67 (20 px), kraj 0.5 (15 px,
pozycje kraju bez zmian). Launcher lidera 154,299 → 152,270, partii 18,368 → 228,310,
editor partii 18,304 196×62 → 18,300 250×66 z ramkami. Render i hit area po skalowaniu
wymagają runtime QA. Zmiana unieważnia hashe review D5D9C80F (dwa .gui, check.py,
native-contract.json, README, lokalizacja rn_in_place_ui, static-review.json).

Read-only „QA guards” nadal jest
diagnostyką tego kandydata, nie testem tekstu ani elementem docelowego produktu.

W obecnym runtime QA bazowego wariantu GetLeader/GetRulingParty i tooltips
odczytują zapis, lecz natywne wiersze lidera/partii odświeżają się dopiero po
ponownym otwarciu polityki. Native refresh bada osobny agent. Ten kandydat nie
rozwiązuje tego problemu i nie udaje odświeżenia własną kopią tekstu. Dowód
bazowego uruchomienia: [day2-inline-apply-run.json](../../docs/evidence/session-20261011/day2-inline-apply-run.json)
oraz [TWELFTH-RUN-NOTES.md](../../docs/evidence/qa-20261011-day2/TWELFTH-RUN-NOTES.md).
Wcześniejszy dowód literału/serializacji partii neutrality jest osobny:
[day2-party-literal-save-bytes.json](../../docs/evidence/session-20261011/day2-party-literal-save-bytes.json).
Żaden z tych raportów nie zalicza nowych czterech gałęzi ani tej geometrii.

Dozwolony przyszły co-load: **wyłącznie główny dev mod + ten jeden fixture**.
Zabronione jest współwłączenie dowolnego innego probe moda, szczególnie
rn_in_place_ui, rn_country_inline_ui, rn_inline_leader_transport_qa,
rn_inline_leader_apply_qa, rn_inline_editor_transport_qa, rn_inline_editor_apply_qa,
rn_inline_pair_qa, rn_inline_payload_qa i rn_entry_layout_qa: współdzielą modele, helpery,
klucze albo (layout) tę samą ścieżkę override.
Proces musi używać dokładnie jednego zgodnego wariantu native bridge. Ten katalog
nie zmienia whitelisty ani zasad co-load DLL.

`python probes/rn_inline_editor_product_qa/check.py` wykonuje odczytową kontrolę
AST, hashy i ograniczony istniejący ApplyVM na rzeczywistych nowych źródłach.
Sprawdza wszystkie cztery gałęzie w trzech niepolskich krajach, odrzucenia przed
i po walidacji, cross-product grup/rządów, Cancel po zmianie rządu, capability
kraju, brak kolizji z mod/ i celowo uszkodzone kontrakty wyłącznie w pamięci.
`--write-report` zapisuje tylko lokalny `static-review.json`. Nie uruchamia gry.
Pure single CD171D, pure pair E278DF i sloty RN_PS/RN_PL są kopiami bajt w bajt;
leader i pair Apply są jawnie zmienionymi kandydatami, nie kopiami dawnego runtime.

Przed aktywacją potrzebne są niezależny review i świeże QA własnej kampanii dla
każdej bazowej grupy: prefill obu pól, różne nazwy Unicode, jedno Apply, save/reload;
zmiana grupy przed prefill i przy otwartym drafcie; invalid B; Cancel; granice
player_context; menu/load i draft lifecycle. Statyka nie zalicza parsera HOI4,
działania GUI, setterów, serializacji nowych gałęzi, native focus ani multiplayer.

## Iteracja 3 (po PID42644)

Źródło: SIXTEENTH-RUN-NOTES (realny rename, ołówki 20 px i dedup działają; M1, ciasny
edytor kraju, pojemność pól i globalny przycisk do poprawy) oraz review M1–M3, m1, m2.

- **Enter/Esc bez DLL** (wzorzec vanilla `frontendmultiplayerview.gui:85-94,222-241`):
  wszystkie pięć `editBoxType` ma `ignore_enter = yes`, każde Zastosuj `shortcut = "RETURN"`,
  każde Anuluj `shortcut = "ESCAPE"`. Przyciski leżą wyłącznie w oknach edytorów, których
  `visible` wymaga flagi `*_open`, a ich `_enabled` też jej wymaga. Open kraju/partii wymaga
  braku wszystkich trzech flag, Open lidera zamyka partię, więc otwarty jest najwyżej jeden
  edytor i jedna para skrótów. Enter wywołuje ten sam selektor `*_apply_click`, a więc tę samą
  komendę, guardy epoki i dedup. Ryzyka: politics `close_button` też ma ESCAPE (Esc może
  zamknąć panel zamiast lub oprócz Anuluj; flaga i draft zostają, po ponownym otwarciu edytor
  wraca); semantyka `ignore_enter` w HOI4 i przejście shortcutu przez natywny ctor to runtime.
- **M1:** ołówek lidera 154,242 20×20 — prawy dolny róg portretu, bezpośrednio NAD tabliczką
  `leader_name` (18,262), nigdy nad tekstem nazwy. Zakrywa narożnik portretu (20×20), nie twarz.
- **Edytory** (lider, partia, kraj): nakładki 420 px na `GFX_generic_bg2`, pola w ramkach
  `GFX_tiles_dark_area_cut_8` 364×26, pola `hoi_18` 356×20 (32 × najszerszy glif `m`/`W`
  11 px = 352 px wg `.fnt`), Zastosuj 20 px, Anuluj 16 px, linia statusu `Arial12`.
  Kraj: 18,28 420×74, dwa wiersze (nazwa, przymiotnik). Lider: 18,262 420×46. Partia:
  18,300 420×68. Otwarte nakładki czasowo zakrywają frakcję / pie chart / część listy partii /
  górę portretu; wszystkie kończą się przed y383 i w szerokości panelu 550.
- **Pojemność pól:** xadvance przewiduje 32 najszersze znaki w 356 px, ale PID42644 pokazał
  19 „a” w 176 px (hoi_18) i 16 w 238 px (hoi_16mbs), czyli mniej niż sama szerokość. Limit
  CEditBox jest więc runtime OPEN; test: 32×„W” i 32×„a” w każdym z pięciu pól.
- **M3:** odrzucone Apply zapisuje UI-only `rn_ip_status_err/field` (efekty
  `rn_ip_status_record_*` po helperze; `rn_ip_status_clear` przy Open/Cancel/sukcesie).
  Linia statusu pokazuje podpowiedź „Enter/Esc/maks. 32 znaki” albo czerwony błąd pola
  (pusto, ponad 32 znaki, niedozwolony znak — natywne ok=0 nie rozróżnia przyczyny) lub
  „edytor nieaktualny”. Żaden guard/trigger/setter nie czyta tych zmiennych (check.py).
  Kontrakt SG Apply to teraz: log, helper, status, log.
- **Globalny „Zmień nazwy”:** jedyny celowy override tej samej ścieżki co dev mod:
  `common/scripted_guis/rename_anything_scripted_gui.txt` = bajtowa kopia pliku dev moda z
  `rn_entry_gui` `visible = { always = no }` (identyczna z layout fixture).
  `descriptor.template` ma `dependencies={ "Rename Anything" }`, żeby ładował się po dev
  modzie. Layout fixture nie może być wtedy ładowany. Bez decyzji z layoutu stary edytor
  główny nie ma wejścia; ścieżki stanu/miast działają przez widok stanu. Zmiana generatora
  dev moda wymaga odświeżenia tej kopii (check.py porównuje bajty).
- **check.py:** geometria liczona z drzewa GUI (prostokąty z position/scale, rozłączność
  Zastosuj/Anuluj/pól, pola w ramkach, okna w panelu, ołówek lidera poza `leader_name`,
  ołówek partii w `ruling_party_info`), szerokość ≥ 32×najszerszy glif, skróty tylko na 6
  przyciskach, wyłączność Open, status tylko w UI, dokładny override; 10 odrzuconych mutacji.
- **Cooldown zmiany nazwy (5 dni gry, osobno: państwo+przymiotnik, lider, partia):**
  jedyna stała `rn_ip_cooldown_days` (`common/scripted_effects/rn_inline_cooldown.txt`).
  Udane Apply (tylko gałąź err=0) zapisuje na kraju `rn_ip_cd_<typ>_until = global.num_days + 5`
  oraz `rn_ip_cd_<typ>_date = global.date` (zmienne kraju są w save). Trigger
  `rn_ip_cooldown_active_<typ>` liczy różnicę temp-zmiennymi w triggerze (wzorzec vanilla
  `ai_strategy/ENG.txt:1729-1731`). W cooldownie ołówek jest widoczny, ale wyłączony
  (`*_open_click_enabled`), Open odmawia, a obie rundy guardu Apply dają błąd 11 (komenda z
  kolejki). Tooltip ołówka pokazuje dokładną liczbę dni (1–30, potem „ponad 30”) i datę
  ostatniej zmiany (`GetDateStringNoHourLong`, jak vanilla BUL). Odrzucone Apply, Cancel i
  błąd walidacji nie startują cooldownu. Typy są niezależne. Czas płynie tylko bez pauzy:
  QA musi odpauzować grę na ≥5 dni. Decyzje vanilla (`days_re_enable`) pokazują pozostały
  czas tylko w panelu decyzji, więc nie nadają się do ołówków scripted GUI.

## Iteracja 4 (po PID49352)

- **Esc:** z Anuluj usunięto `shortcut = "ESCAPE"`. W panelu polityki Esc należy do vanilla
  `close_button` (`countrypoliticsview.gui:634`) i w PID49352 zamknął panel, zanim zadziałał
  nasz przycisk. Wszystkie modele edytorów nadal mają `parent_window_token = politics_tab`.
  To, że edytor został na ekranie po zamknięciu panelu, jest **otwartym defektem runtime**
  (hipoteza: fokus CEditBox). Flaga, pin i epoka zostają, więc po ponownym otwarciu panelu
  edytor wraca z draftem bez zmiany nazwy, a Anuluj działa. Podpowiedź: „Enter: zatwierdź”
  (bez obietnicy 32 znaków, dopóki pojemność pól jest niezmierzona).
- **Kraj:** nazwa i ołówek są w linii tytułu panelu (150,8): nazwa `hoi_18mbs`,
  `format = right`, kończy się przy ołówku 20 px (434..454), więc dłuższa rośnie w lewo; przed
  ikoną zasad (x460). Vanilla nie ma tu tekstu nazwy kraju (tylko `political_title`), więc
  dawny podpis 45,29 był nasz — nic nie nadpisujemy w vanilla `.gui`.
- **Partie:** edytor 18,266 420×102 ma 4 zakładki (vanilla `GFX_button_94x31`, jak zakładki
  głównego edytora; wybrana jest wyłączona). Zakładka = `rn_inline_pair_switch_party`:
  nowy pin THIS, grupa, epoka +1. Bridge prefilluje ponownie przy nowej epoce (render bridge:
  `state.epoch!=epoch` → nowe `attempted`), chyba że pole ma fokus (wtedy zachowuje draft).
  Grupa nie musi rządzić: `set_party_name` z dowolną ideologią jest używany przez vanilla
  (np. `national_focus/poland.txt:11717`). Krótka nazwa nierządzącej partii z
  `Get<Grupa>Party`; długiej gra nie podaje, więc pole długie dostaje znak „?”
  spoza alfabetu (I4-M1): niezmienione Zapisz natywny enkoder odrzuca (ok=0 -> błąd 1, pole 2),
  setter się nie wykonuje, a status mówi „Wpisz pełną nazwę partii w miejsce „?””.
  Przełączenia zakładki przy fokusie w polu skrypt nie wykrywa (bridge nie wystawia tego stanu). Każdy kraj ma partie 4 bazowych grup (także przy 0% poparcia).
  Cooldown partii pozostaje jeden dla wszystkich partii (prostszy, spójny z kategoriami).
- **Podmioty:** ukryty placeholder `rn_ip_subject_gui` (`diplomacy_target_context`) z trzema
  ołówkami; przełączniki `rn_ip_subject_rename_enabled` i `rn_ip_subject_country_capability`
  są `always = no`, efekty tylko logują. Wymaga nowych modeli native.

