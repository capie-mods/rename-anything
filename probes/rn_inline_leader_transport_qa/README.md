# Niewłączona próba transportu pola lidera

Stan 2026-10-11: osobna kopia aktualnego `../rn_in_place_ui` do jednorazowej
próby z `rename_anything_inline_leader_bridge.dll`. Nie zarejestrowano jej ani
nie aktywowano; nie wykonano build, injection, UI ani testu w grze.

**Nie ładować razem z `rn_in_place_ui`.** Obie fixture deklarują te same modele,
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
Obecny natywny lifecycle jest per-model i nie przypina stanu prefill do konkretnej
instancji window/root; hidden tick może rozpocząć ponowny prefill w tej samej
epoce. Nie zakładamy, że menu/load zawsze daje hidden tick. Stary mod nadal może
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
