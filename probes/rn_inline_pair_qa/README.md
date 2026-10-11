# Niewłączony fixture walidacji dwóch payloadów

Stan: źródła do niezależnego przeglądu root. Nie zarejestrowano moda, nie
zmieniono konfiguracji ani aktywnych plików, nie uruchomiono gry. Brak dowodu
runtime dla nowego helpera pary i tego fixture. Nie wymaga DLL i nie testuje
transportu pola natywnego, settera partii ani zmiany nazwy kraju/postaci.

`rn_inline_pair_validate` waliduje A (`rn_native_ok/len/0..31`) i B
(`rn_nativeb_ok/len/0..31`) przez niezmieniony strict single helper. Odrzuca A
przed aliasowaniem B. Przy poprawnym A kopiuje wszystkie34 wartości do
prywatnych tempów `rn_paira_*`, aliasuje B na wejście single helpera, zachowuje
wynik B i zawsze odtwarza wszystkie34 A. B pozostaje tylko do odczytu.
Nie zmienia buforów persistent, flag, celów, epoki ani nazw.

Wynik to tempy `rn_pair_err`, `rn_pair_field`, `rn_pair_bad`:

| Wynik | err | field | bad |
|---|---:|---:|---:|
| Oba pola poprawne | 0 | 0 | -1 |
| Niepoprawny marker | 1 | 1 lub2 | -1 |
| Długość poza1..32 lub ułamkowa | 4 | 1 lub2 | -1 |
| Kod aktywny poza1..84 lub ułamkowy | 5 | 1 lub2 | indeks0..31 |
| Niezerowy padding | 6 | 1 lub2 | indeks0..31 |

Pierwsze błędne pole wygrywa. `rn_inline_*` są scratch i po odtworzeniu A mogą
nadal zawierać wynik B; caller używa wyłącznie `rn_pair_*`. Prywatne tempy
backup są nadpisywane. Helper nie zachowuje poprzednich scratch/output tempów.

Walidacja pary sama nie uprawnia do Apply. Przyszły caller musi ponownie
sprawdzić własny kraj/cel, epokę, aktualną partię oraz capability kraju, zanim
zapisze jakikolwiek właściwy bufor. Ten fixture nie implementuje tych guardów,
ich testów ani setterów. `rn_ip_cmd_epoch` i `rn_native_cap` w `contract.json`
to wyłącznie inwentaryzacja przyszłych nazw; żaden przycisk ich nie używa.

## Izolacja i późniejszy runtime

Root powinien przejrzeć źródła i świadomie włączyć tylko ten fixture w nowym
procesie, na disposable save własnego POL. Można użyć głównego moda, aby
obserwować rzeczywiste bufory. Nie ładować równolegle `rn_in_place_ui`,
`rn_inline_payload_qa`, `rn_inline_leader_apply_qa` ani innego fixture
definiującego te same helpery.
Kopia single helpera musi być byte-identyczna; nie dodawano aliasów jego nazw.
Nowy helper pary jest identyczny z nowym plikiem w niewłączonym
`rn_in_place_ui/common/scripted_effects/rn_inline_pair_payload.txt`.

Jawnie dopuszczone po przeglądzie źródeł jest jedno połączenie izolowanego QA:
`mod/` + `probes/rn_inline_leader_transport_qa/` + ten fixture. Transport QA
nie definiuje single/pair helpera, a jego leader Apply wyłącznie loguje;
party Apply pozostaje disabled. Exact inventory w `co-load-review.json`
nie wykazało kolizji globalnych efektów, modeli SG, okien, sprite'ów,
lokalizacji ani wirtualnych ścieżek plików. Callbacki SG i kontrolki GUI są
porównywane w obrębie ich modelu/okna, zgodnie z rzeczywistym zakresem nazw.
Transport Open/Cancel zapisuje własne `rn_ip_*`; przyciski pair zapisują tylko
prywatne `rn_prq_bak0..4`. Te zbiory zapisów się nie przecinają.

To dopuszczenie dotyczy wyłącznie wersji transport-only, bez rzeczywistego
rename Apply. Syntetyczne `rn_native_*` w pair są tempami oddzielnej komendy
`rn_prq_gui`, nie rekordami wstrzykiwanymi do modelu editora. Native mostek
lidera przyjmuje tylko `rn_ip_leader_gui` / `rn_ip_leader_apply_click`; pair
nie jest na jego whiteliście. Nie wolno użyć pair jako producenta payloadu
dla Apply lidera ani uznać PASS pary za PASS native transportu. Fresh-command
lifetime tempów i oba etapy nadal wymagają osobnych obserwacji w grze.
Root może zaplanować je w jednym świeżym procesie, zachowując te ograniczenia.

`rn_prq_gui` ma `player_context`, domyślny main-window parent, okno
`(900,80)290x208`. Rozdzielczość i clipping wymagają oględzin. Sześć przycisków
ma identyczny guard enabled i efektu: POL, is_ai=no, NOT rn_input, NOT rn_open.
Samo is_ai=no nie jest guardem multiplayer. Nie ma natywnego editboxu ani
zgodności z whitelistami native bridge. Multiplayer odłożono.

Sprawdzić error.log po ładowaniu i przed każdym kolejnym etapem. Wykonać
przyciski w poniższej kolejności; każdy jako osobne kliknięcie/komendę SG.
Przy FAIL przerwać, zachować logi i save; nie zaliczać pozostałych prób.
Poniższe wyniki są oczekiwaniami, nie logami z gry.

| Przycisk | Case IDs | Co porównuje |
|---|---|---|
| Valid1/32 | 1,2 | A1/B32 i A32/B1 z różnymi kodami |
| Invalid A | 100..116 |17 błędów pola A, B poprawne |
| Invalid B | 200..216 |17 błędów pola B, wszystkie34 A zachowane |
| Both invalid | 300 | Oba markery0, priorytet pola A |
| Missing A | 301 | Marker A celowo nieutworzony w nowej komendzie |
| Missing B | 302 | Marker B celowo nieutworzony, A32 zachowane |

W grupach Invalid: marker0/2, długość0/33/1.5/1.00001/31.99999,
aktywny kod0/85/1.5/1.00001/83.99999, ostatni aktywny slot31=0/85,
padding slot1=1 i slot31=1/0.00001. Każdy przypadek przygotowuje wszystkie68
wejść od zera z poprawnymi aktywnymi kodami, poza dwoma celowymi brakami
markerów. A32 zawiera84..53, B32 zawiera1..32; różnice wykrywają zamianę pól
i zgubiony tail. Każda próba B zaczyna z pełnym, odrębnym A32.

Brak markera testuje osobna świeża komenda, ponieważ vanilla nie dokumentuje
`clear_temp_variable`. Producent tej komendy pomija przypisanie danego markera
i nie wywołuje wcześniejszego producenta. Oczekujemy odczytu braku jako0.
Porównanie wartości nie rozróżnia braku rekordu od jawnego0; nie dowodzi więc
zachowania obecności temp-record. To wymaga kontroli fresh-command w runtime.
Nie uruchamiać Missing przez wywołanie zbiorczego efektu w tej samej komendzie.

## Uczciwe porównania i brak modyfikacji buforów

Przed walidacją QA zapisuje niezależne68 tempy `rn_prq_a/b_*`, a po niej
porównuje każdy z oryginałem; nie czyta backupu produkcyjnego `rn_paira_*`.
Porównuje także wszystkie elementy i rozmiary pięciu rzeczywistych buforów:
`rn_buf`, `rn_cname`, `rn_cadj`, `rn_pshort`, `rn_plong`, oraz wartość i
obecność każdej odpowiadającej zmiennej długości. Istniejące puste/brakujące
bufory są dopuszczalne; obecność samego pustego array nie jest testowana.

Jedynymi trwałymi zapisami QA są pięć prywatnych array snapshotów
`rn_prq_bak0..4`. Są czyszczone po każdym przypadku. Długości, expected values,
liczniki różnic i kopie obu payloadów są wyłącznie tempami. Nie zapisuje się
żadnego z pięciu właściwych buforów ani ich długości, nawet po FAIL. Nie ma
rollbacku ani zmiany flag/targetów. Nie wywołuje się `rn_inline_copy_payload`.

Każdy log PASS jest warunkowy: rzeczywisty err/field/bad musi równać się
oczekiwanym wartościom i wszystkie trzy liczniki różnic muszą wynosić0.
Log zawiera wartości odczytane po porównaniu, np. oczekiwane:

```text
RN_PRQ case=1 PASS err=0 field=0 bad=-1 adiff=0 bdiff=0 pdiff=0
RN_PRQ case=200 PASS err=1 field=2 bad=-1 adiff=0 bdiff=0 pdiff=0
RN_PRQ case=215 PASS err=6 field=2 bad=31 adiff=0 bdiff=0 pdiff=0
```

Pełna tabela wejść i oczekiwań znajduje się w `contract.json`. Prawidłowy pełny
runtime daje39 takich logów PASS, zero FAIL i zero nowych błędów parsera.
Samo wyświetlenie okna lub brak error.log nie zalicza porównań.

## Kontrole offline i granica dowodu

```powershell
python probes/rn_inline_pair_qa/tools/generate.py
python probes/rn_inline_pair_qa/tools/check.py
python probes/rn_inline_pair_qa/tools/co_load_review.py
```

Generator zapisuje tylko ten fixture i przydzielony nowy helper pary w
niewłączonym rn_in_place_ui. Single helper jest kopiowany jako niezmienione
bajty (SHA256 CD171D6203BD66DC7905C7C3D0E1A2750C4B8EABAB45F0540D75D3AF2CE10800).
Checker wykonuje faktyczny sparsowany kod helperów w małym modelu tempów,
warunków i array oraz audytuje osiągalny callgraph: pure validator nie ma
trwałych zapisów, a QA zapisuje wyłącznie swoje snapshoty. Sprawdza41 wejść
pary,39 obserwacji QA i mutację gubiącą restore slot31; mutacja musi dać FAIL
również w samym kodzie QA (`adiff=1`). To dowód logiki źródła przy przyjętych
regułach modelu, nie parsera i semantyki HOI4. Wynik zapisuje static-review.json.

Primary syntax pochodzi z lokalnego HOI4: documentation/effects_documentation.md
(set_temp_variable, round_temp_variable, for_each_loop),
documentation/triggers_documentation.md (check_variable, has_variable) oraz
common/scripted_guis/_documentation.md (player_context/main-window parent).
Strict single helper z round-and-compare zaliczył osobne wcześniejsze runtime
QA; nowe aliasowanie obu pól, przywracanie, snapshoty i Missing nadal wymagają
rzeczywistego wykonania tego fixture po przeglądzie root.
