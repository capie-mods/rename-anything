# Niewłączona próba transportu pola lidera

Stan 2026-10-11: osobna kopia `../rn_in_place_ui` do próby z
`rename_anything_inline_leader_bridge.dll`. Pierwszy proces PID3188 został
zamknięty przez root po niepotwierdzonym Open/prefill (screenshot89–91).
Poniższa rewizja geometrii i diagnostyki guardów nie została jeszcze uruchomiona;
w tym kroku nie wykonano build, injection, konfiguracji ani UI.

**Nie ładować razem z `rn_in_place_ui` ani `rn_inline_leader_apply_qa`.** Obie fixture deklarują te same modele,
kontrolki i helpery. Do tej próby root wybiera tylko jedną z nich. W procesie
nie mogą współistnieć DLL editor-observer, editor-bridge i inline-prefill z
inline-leader-bridge: hookują te same funkcje. Main mod kraju jest osobną
zależnością sesji; ten katalog nie zmienia jego plików ani konfiguracji.

Zachowano geometrię vanilla, wszystkie dokładne nazwy wymagane przez mostek,
trzy natywne pola lidera/partii i pięć hidden carrierów. Ich aktualne nazwy
są rozwiązywane dynamicznie, bez wpisania „Jan Żółć” na stałe w GUI. Open lidera
kopiuje typed pin własnego aktualnego władcy, zmienia flagi i epokę jak w źródle;
Cancel czyści pin/flagę i zwiększa epokę. Partia nadal ma osobne pola short/long,
Open/Cancel, a jej Apply pozostaje `always = no`.

Jedynym nowym aktywnym działaniem po przycisku jest **logowanie**. Leader Apply
jest enabled przy własnym `player_context` POL, otwartym editorze, dodatniej
`rn_ip_epoch`, istniejącej identity i singletonie target zawierającym tę identity.
`any_character` w bieżącym COUNTRY ponownie wymaga własnego aktywnego władcy
obecnego w tym target. Enabled i sam efekt odrzucają stare `rn_open`/`rn_input`, otwartą
partię i edycję kraju. Guard nie zależy od payloadu ani transportowanej epoki:
natywny dispatch ocenia enabled przed wstrzyknięciem rekordów przez konstruktor.
Wszystkie launchery i editory są również ukryte przy obu flagach legacy, a Open
ponawia te blokady w enabled i efekcie/helperze. Nie polegamy na odświeżanej
w ticku desired visibility. Disabled Apply partii nadal pozostaje `always = no`
i ma te same blokady w logującym placeholderze. Cancel nie dostał ograniczeń.

Efekt `rn_inline_leader_apply` został w tej kopii całkowicie zastąpiony logiem.
Wypisuje ok, len, wszystkie 32 sloty, `temp_var:rn_ip_cmd_epoch` i persistent
`ROOT.rn_ip_epoch`. Nie waliduje ani nie akceptuje tekstu; nie woła payload-copy,
nie dotyka `rn_buf/rn_len`, nie zmienia nazw i nie zamyka editora. Odrzucenie
kontekstu/pina/epoki też tylko loguje. Żaden wynik nie jest oznaczany jako PASS.
`rn_inline_payload.txt` i rzeczywista logika rename Apply nie są dołączone.

`native-contract.json` podaje dokładny kontrakt. Istotna ścieżka mostka to
`rn_ip_leader_gui` / `rn_ip_leader_edit` / `rn_ip_leader_apply_click`, carrier
`rn_ip_leader_prefill` i epoka `rn_ip_leader_epoch` z `[?ROOT.rn_ip_epoch|0]`.
Mostek ma świeżo rozwiązać View/pole/epokę, skopiować UTF32, wyczyścić dokładne
35 reserved keys i dodać ok/len/32codes/epoch. Nie ma transportu partii ani kraju.
Enter pozostaje wyłącznie diagnostyką; to kliknięcie Apply jest źródłem payloadu.
Bez właściwej DLL przycisk może pokazać brakujące albo stare temp wartości.
Samo dojście do logu nie dowodzi, że natywny mostek był obecny.

Oczekiwany początkowy tekst aktualnego lidera opisuje `expected-input.json`:
„Jan Żółć”, 8 codepoints, 12 bajtów UTF8, ok1, len8, sloty
`36,1,14,63,84,72,70,68`, następnie 24 zera. Kody obliczono z dokładnych
przypisań `CHARS` w `tools/gen.py`, bez uruchamiania generatora. Jeśli save ma
już innego lidera albo nazwę, należy porównać faktyczny resolved carrier i dane
natywnego snapshotu; fixture nie wymusza tej przykładowej nazwy.

Po świadomej aktywacji przez root oczekiwane obserwacje z logu mają postać:

```text
RN_ILQA payload ok=1 len=8 cmd_epoch=E persistent_epoch=E
RN_ILQA slots 00-07: 36,1,14,63,84,72,70,68
RN_ILQA slots 08-15: 0,0,0,0,0,0,0,0
RN_ILQA slots 16-23: 0,0,0,0,0,0,0,0
RN_ILQA slots 24-31: 0,0,0,0,0,0,0,0
```

`E` jest dodatnią epoką tego otwarcia, nie ustaloną stałą. Format liczb w logu
może zależeć od parsera/renderera; literalny namespace `temp_var:` i dokładne
odczyty wymagają runtime proof. Nie wolno uznać zera/braku ostrzeżeń za sukces.
Dobrze odczytany, ale nieobsługiwany/pusty/zbyt długi tekst ma dać ok0, len0
i wszystkie 32 sloty0, przy nadal transportowanej epoce. Snapshot nieczytelny
lub przekraczający limit 128 codepoints ma być odrzucony przez mostek przed
dispatch. Porównanie native RN_ILBR i script RN_ILQA musi obejmować każdy slot,
epokę, invalid fullzero oraz zachowanie obcych rekordów; ten katalog nie dodaje
syntetycznego producenta rekordów.

Ta próba ma wyłącznie ustalić transport w jednym otwarciu. Nie zalicza menu/load,
zmiany gracza, zapisu ani zachowania draftu po przejściu do innej zakładki.
Rewizje natywnego lifecycle są osobnym zadaniem root/reviewera; ta korekta GUI
nie dowodzi resetu instancji window/root ani zachowania draftu. Nie zakładamy,
że menu/load zawsze daje hidden tick. Stary mod nadal może
otworzyć legacy okno w drugą stronę: inline ukryje się, a guarded Open/Apply
odrzuci `rn_open` i `rn_input`. Te blokady nie anulują draftu ani flag inline
i nie rozwiązują polityki resetu; starego moda i natywnego lifecycle nie zmieniono.
Flagi/epoka są skryptowym stanem kraju, więc wymagają osobnej polityki
resetu i testów. Multiplayer jest odłożony.

Primary źródła: `GAME/common/scripted_guis/_documentation.md:11,20,29` dla
player_context/politics_tab; `GAME/documentation/triggers_documentation.md:1272-1279`
dla COUNTRY any_character. Aktywny władca i własność typed pina są opisane w
`../../docs/evidence/session-20261011/day2-leader-party-native-review.txt`.
Kontrakt konstruktora i exact transport:
`../../docs/evidence/session-20261011/day2-native-command-contract.txt` oraz
`../../docs/evidence/session-20261011/day2-inline-leader-bridge-codec-review.txt`.
`GAME = C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV`.

`static-review.json` zapisuje inventory, dokładne zachowanie odziedziczonych
helperów, różnice od źródła i SHA256. Jest to kontrola źródeł, bez potwierdzenia
parsera gry, rzeczywistego prefill, klawiatury, logów czy transportu komendy.


## Korekta geometrii po zakończonym PID3188

Zmieniono wyłącznie geometrię lidera, bez zmiany parenta lub origin:
launcher `(154,299)` 14×14, editor `(18,262)` 155×36, natywne pole lokalnie
`(4,8)` 110×20, save `(117,10)` 16×16, Cancel `(135,10)` 16×16.
Pole i przyciski kończą się przed lokalnym x173, w obrębie natywnego wiersza
`leader_name`. Launcher leży tuż pod nazwą, przed tekstem ideologii od y313.

Vanilla `countrypoliticsview.gui:94–141` składa pozycję Create faction do
`(180,243)`; `interface/factions/factions.gfx:740–742` wskazuje DDS573×57
z trzema klatkami, czyli 191×57 na klatkę. Poprzednie `(177,273)` oraz prawy
Cancel nachodziły na ten przycisk. Na screenshot89–91 źródłowy overlap wyjaśnia
natywne tooltipy, ale nie stanowi dowodu wykonania callbacka inline. Nowa
geometria, z-order, hitbox, widoczność i Open/Cancel wymagają świeżego QA.
Nie zmieniono modelu, named controls, carrierów, epoki, guardów ani helperów.


## Odczyt guardów bez zmiany stanu

Dodatkowy model `rn_ilqa_guard_gui` ma własny `player_context`, `politics_tab`
i guard własnego POL (`is_ai = no`). Przycisk **QA guards** leży lokalnie
`(375,760)`, 148×36: w obecnym disposable client1720×900 poniżej ikon personelu
wojskowego. Przykładowe y700 nachodziłoby na ich wiersz. Krótsze okno i inna
skala UI wymagają osobnej kontroli.

Model celowo nie znika przy `rn_open/rn_input` ani inline-open: ma ujawnić
przyczynę ukrycia launchera. Enabled i callback ponawiają własny POL/is_ai=no.
Callback wyłącznie loguje `RN_ILQA guards`: rzeczywisty `[ROOT.GetTag]`,
`rn_ip_epoch`, count typed pina oraz osobną linię true/false dla `rn_open`,
`rn_input`, `rn_ip_leader_open`, `rn_ip_party_neutrality_open`,
`rn_ip_country_open`. Nie ustawia/usuwa flag, zmiennych, epoki, tablic ani tempów,
nie odczytuje/produkuje payloadu, nie woła Open/Cancel/Apply/rename.

To osobny diagnostyczny selector `rn_ilqa_guards_click`, bez natywnego pola
lub carrierów, poza whitelist bridge. Log nie emituje PASS. Brak wpisu nie
rozstrzyga sam, czy przycisk był niewidoczny, disabled, czy callback nie dotarł.

Grafika diagnostyki `GFX_button_148x34` ma w dokładnej instalacji DDS148×36;
kontener dopasowano do rzeczywistej wysokości36, bez skalowania.
