# Niewłączona diagnostyka semantyki payloadu

Stan 2026-10-11: osobny disposable fixture, bez rejestracji `.mod`, aktywacji,
sterowania grą, builda DLL i zmian aktywnych plików. Same deterministyczne efekty
skryptowe; nie stanowią dowodu transportu natywnego pola ani zwykłej komendy.
Nie zmieniają nazw ani targetów. Nie wywołują rn_apply_input/rn_open_input.

Model `rn_pqa_gui` to player_context własnego POL, bez parent_window_token
(domyślny main window). Okno `(900,80)290x208` leży na prawym obszarze mapy,
poza aktywnym native probe local politics `(180,430)340x224`. Rozdzielczość,
skalowanie i clipping nadal wymagają oględzin. Wszystkie sześć przycisków ma
własne nazwy rn_pqa_* i guard POL/is_ai=no/NOT rn_input. Nie ma editBoxType,
selectorów rn_native_probe_* ani pokrycia whitelist aktualnego bridge.
Player_context daje lokalny kraj; samo is_ai=no nie jest guardem MP.

## Co ładować później

Root może świadomie załadować ten fixture wraz z głównym modem i rn_native_input,
po zakończeniu obecnego QA. Nie aktywuje się sam. Nie ładować jednocześnie
rn_in_place_ui: `common/scripted_effects/rn_inline_payload.txt` jest dokładną
kopią testowanego helpera z tego katalogu, z tymi samymi nazwami efektów.
Skopiowano go bez zmiany bajtów; SHA podano niżej. Własne efekty diagnostyczne
mają odrębny prefix rn_pqa_*. Zmiana źródłowego helpera wymaga ponownego
porównania kopii, a nie dwóch odmiennych definicji ładowanych naraz.

## Kolejność i oczekiwane logi game.log

Najpierw sprawdzić error.log po samym załadowaniu. Brak błędów parsowania nie
potwierdza jeszcze semantyki. Uruchomić Namespace jako pierwszy. Przy każdym
FAIL przerwać dalsze testy, zachować game.log/error.log i nie zaliczać następnych
kroków. Copy valid zostawić po poprawnych testach czystego validatora.
Wartości liczbowe poniżej są oczekiwane, nie zaobserwowane.

| Przycisk | Oczekiwany log / sens |
|---|---|
| Namespace | `RN_PQA namespace PASS temp=7 scalar=7 array=7` |
| Validate 1 | `RN_PQA case=1 PASS err=0 bad=-1 unchanged=1` |
| Validate 32 | `RN_PQA case=2 PASS err=0 bad=-1 unchanged=1` |
| Invalid set | pięć wyników z poniższej tabeli, każdy unchanged=1 |
| Copy valid | `RN_PQA copy-valid PASS err=0 len=2 codes=1,84`, potem `RN_PQA restored PASS` |
| Copy reject | `RN_PQA copy-reject PASS err=6 bad=31 unchanged=1` |

| Case | Celowe wejście | Oczekiwany err | bad |
|---|---|---|---|
| 31 | sentinel rn_native_ok=0 | 1 | -1 |
| 32 | rn_native_len=1.5 | 4 | -1 |
| 33 | pierwszy aktywny kod=85 | 5 | 0 |
| 34 | pierwszy aktywny kod=1.5 | 5 | 0 |
| 35 | ostatni padding slot31=1 przy len1 | 6 | 31 |

Namespace tworzy prywatną zwykłą rn_pqa_source=99 i temp o tej samej nazwie=7.
Jawny temp_var: musi odczytać7 w check_variable LHS, set_temp_variable RHS,
set_variable RHS oraz add_to_array RHS; prywatny scalar/array muszą dostać7.
Nie jest to dowód zachowania żadnej nazwy kraju/postaci. Pola prywatne są po
próbie czyszczone. Liczba99 jest kontrolą kolizji podczas przygotowania wejścia,
nie osobnym odczytem trwałej zmiennej po ustawieniu temp o tej samej nazwie.

Każdy producent wejścia najpierw ustawia WSZYSTKIE34 tempvars na0, a potem
sentinel/len/aktywne kody dla danego przypadku. Validate32 ma kody1..32;
Copy valid ma dokładnie1,84 (dolna/górna granica alfabetu). Nie ma założenia,
że tempvars przetrwają poprzedni przycisk, ani dopuszczenia częściowych danych.
To nadal wartości ustawione skryptem, a nie świeże rekordy z konstruktora native.

## Bufor i odrzucenie

Namespace dotyka wyłącznie własnych prywatnych zmiennych/array rn_pqa_*.
Pozostałe testy robią pełny prywatny snapshot rn_buf oraz wartości i obecności
rn_len. Porównanie sprawdza rozmiar array, każdy element, długość i obecność
zmiennej. Do snapshotu/restore użyto istniejącej składni implicit loop temp
(value/index), aby nie odtwarzać bufora przez testowany explicit temp_var:.

Validate1/32/Invalid set wywołują pure-temp rn_inline_validate_payload; przed
sprzątaniem logują, czy bufor pozostał identyczny. W przypadku nieoczekiwanej
zmiany następuje próba rollbacku z osobnym `restored PASS/FAIL`, bez zamiany
pierwotnego FAIL w PASS. Copy reject sprawdza to samo po wywołaniu copy helpera.

Copy valid jako jedyny zamierzenie podmienia rn_buf/rn_len na2 kody, sprawdza
pełny wynik i zawsze odtwarza wcześniejszy bufor oraz stan obecności rn_len.
Robi to w jednym synchronicznym efekcie, bez zmiany nazw czy celów. Prywatne
snapshots są potem czyszczone. Tę próbę wykonać wyłącznie w disposable QA save;
restore jest kandydatem skryptowym, dopóki runtime nie zaliczy odpowiedniego logu.
Nie testuje flags/targetów Apply i nie otwiera wielkiej klawiatury.

## Primary i granice dowodu

GAME = C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV.

- common/scripted_guis/_documentation.md:11,20,25-29: player_context oraz
  domyślny main-window parent przy braku parent_window_token.
- documentation/triggers_documentation.md:2110-2130: check_variable porównuje
  zmienne/liczby i dokumentuje krótką składnię używaną przez helper.
- documentation/effects_documentation.md:4279-4295: for_each_loop value/index
  to tempvars; główny mod używa tej składni do kopii buforów (rn_store_country_name).
- events/LaR_Portugal.txt:951-962 oraz common/on_actions/05_lar_on_actions.txt:45-56
  używają literalnego namespace temp_var: w random_list weights. Nie dowodzą
  dokładnych callerów check_variable/set_variable/add_to_array — dlatego te
  przyciski są potrzebne. Genericzny native resolver546530 obsługuje namespace,
  ale sam nie zalicza tych konkretnych ścieżek parser/runtime.
- Sprites/fonts: istniejące GFX_tiled_window_2b_border, GFX_button_123x34,
  hoi_18mbs i hoi_16mbs; składnia buttonType pochodzi z obecnego probe/vanilla.

Parser, semantyka efektów, snapshot/restore i logi nie zostały sprawdzone w grze.
Zero findings kontroli statycznej nie oznacza PASS runtime. Dalszy etap musi
osobno połączyć rzeczywistą świeżą komendę native z validator/copy; ten model
nie znajduje się w native whitelist i nie wolno udawać, że testuje transport.

Copied helper SHA256: cd171d6203bd66dc7905c7c3d0e1a2750c4b8eabab45f0540d75d3af2ce10800

## Korekta po pierwszym przebiegu

PID16992 zaliczył namespace, Validate1/32 i cases31/33/35. Cases32/34 FAIL:
`modulo_temp_variable` z dzielnikiem1 nie odrzuciło wartości1.5. QA przerwał
przed Copy valid/reject; nie wykonano zmiany nazwy. Sam parser nie zgłosił błędu.
Helper zastąpiono porównaniem zaokrąglonej prywatnej kopii z nienaruszonym
wejściem. Ta poprawka wymaga nowego procesu i pełnej powtórki.

Invalid set ma dodatkowo cases36/37 (len1.00001/31.99999, err4,bad-1),
38/39 (pierwszy kod1.00001/83.99999, err5,bad0), 40/41 (len0/33,err4,bad-1).
Każdy ma wymagać unchanged1. To także sprawdzenie dokładności porównania
w natywnym fixed-point silnika, bez założenia tolerancji liczb zmiennoprzecinkowych.
