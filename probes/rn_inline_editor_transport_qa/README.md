> **WYCOFANY (integracja z mod/, 2026-10-11).** Ten probe definiuje te same modele `rn_ip_*`,
> efekty lub klucze co `mod/` (źródło `tools/inline_editor/`, generator `tools/gen.py`).
> **Nie ładuj go razem z `mod/`**: dałoby to duplikaty definicji albo cofnęło zmiany generatora.
> Zostaje w repo jako historia QA; deskryptor w profilu wyrejestrowuje root.

# Niewłączona wspólna próba transportu pięciu pól

Stan 2026-10-11: nowa fixture do przeglądu, bez rejestracji, aktywacji, zmian
konfiguracji, DLL, procesów czy UI. Root wybierze świeży proces dopiero po
zakończeniu bieżącego proof PID43444 i review tych źródeł. Zależności przyszłej
próby: główny mod, kandydat country DLL z RNCountryCapabilities oraz nowy
`rename_anything_inline_editor_bridge.dll`. Nie używać starego leader bridge
jako producenta pary lub capabilities.

**Nie ładować razem z innymi inline fixture:** `rn_in_place_ui`,
`rn_inline_leader_transport_qa`, `rn_inline_leader_apply_qa`,
`rn_country_inline_ui`, `rn_inline_pair_qa`, `rn_inline_payload_qa`.
Nazwy modeli/kontrolek lub helperów nakładają się. W procesie ma być tylko jeden
editor bridge; starsze observer/editor bridge/prefill/leader DLL są wykluczone.

## Zakres diagnostyczny

| Edytor | Pola | Świeże rekordy |
|---|---|---:|
| Lider | nazwa przypiętego własnego aktualnego lidera | 35: A+epoka |
| Partia neutralna | krótka/pełna nazwa aktualnej partii rządzącej | 69: A+B+epoka |
| Własny kraj | nazwa/przymiotnik | 70: A+B+epoka+cap |

Wszystkie modele pozostają w `player_context`/`politics_tab`, własne POL,
`is_ai=no`. Partia dodatkowo wymaga bieżącego `has_government=neutrality`.
Enabled partii wymaga otwartej partii, dodatniej persistent epoki i braku
lidera/kraju/legacy; enabled kraju analogicznie odrzuca lidera/partię/legacy.
Nie sprawdzają payloadu, command epoch ani cap przed ctor: te temp values
wstrzykuje dopiero natywny konstruktor. Efekt/helper ponawia ten sam guard.
Nie ma typed pin partii/kraju i nie deklarujemy dowodu ich tożsamości.

Leader Apply zachowuje byte-identical log-only helper z transport QA, z własnym
singleton typed pin i active-ruler guardem. Logi `RN_ILQA payload/slots` obejmują
pełne A i epoki. B/cap nie są świeże w transporcie35 i nie są tak prezentowane.
Party/country Apply wywołują tylko logujące `rn_ieqa_*_apply`:
`RN_IEQA <model> expected_records=... cmd_epoch=... persistent_epoch=...`
(dla kraju także `cap=...`), nagłówki A/B ok/len oraz wszystkie sloty0–31 każdego
pola, po osiem w linii. `expected_records` jest kontraktem, a nie policzonym
skryptowo rozmiarem natywnego wektora. Następnie pure `rn_inline_pair_validate`
loguje rzeczywiste `rn_pair_err`, `rn_pair_field`, `rn_pair_bad`.
Nie ma komunikatu PASS, nawet gdy validator zwróci zero.

Validator potwierdza wyłącznie kody/długości/padding pól. Nie dowodzi świeżej
epoki, capability, tożsamości celu ani obecności mostka. Cap w logu to obserwacja
zwykłego tempvara; właściwy bridge przed dispatch dwukrotnie pyta świeży export
country DLL o dokładne `0x524e4301` i dopiero wtedy wytwarza marker1. Brak eksportu,
zero lub inna wersja ma zatrzymać country dispatch; ten plik skryptowy nie
zastępuje testu tej natywnej bramki. Oczekiwane dane trzeba porównać między
native RN_IEBR i script logami, łącznie ze wszystkimi kodami, epoką i invalid
fullzero. Fixture nie produkuje syntetycznych rekordów ani tekstu.

W żadnym Apply nie ma setterów, kopiowania/czyszczenia `rn_buf/rn_len`, zmian
flag/epoki ani zamykania edytora. Open/Cancel zachowują odziedziczony przepływ
flag, typed leader pina i epoki. „QA guards” local375,760 (148×36) nadal tylko
odczytuje aktualny tag, legacy/inline flags, epokę i pin count; pozostaje poza
whitelist i nie jest testem transportu. Enter w bridge nadal jest diagnostyką.

## Niezmienione kopie i geometria

Skopiowano byte-identical strict single helper CD171D… i pair helper E278DF…
z aktywnego `rn_inline_pair_qa`, bez zmiany jego źródeł. Pełny single plik zawiera
także definicję copy helpera, ale żaden Apply ani validator tej fixture go nie
wywołuje. Pure pair helper tylko tymczasowo aliasuje B na A i odtwarza poprawne
A; nie wykonuje persistent writes. Dokładne SHA256 są w `native-contract.json`.

Lider zachowuje poprawioną geometrię: launcher154,299, editor18,262 155×36,
field4,8 110×20, save117,10 i Cancel135,10. Partia zachowuje pozycje i pola bazowego
transport QA. Wszystkie trzy grupy mają teraz jawne rozmiary przycisków opisane niżej. Dwa modele kraju i ich geometria/carriery pochodzą
z `rn_country_inline_ui`: launcher45,29, edytor45,28 405×16. Razem modele mają
unikalne nazwy, pięć natywnych pól i osiem hidden carrierów. Nowe korzenie kraju
nie nachodzą na korzenie lidera/partii ani QA guards; launcher/editor tej samej
grupy są celowo alternatywami zależnymi od flagi. Native clipping/z-order/skala
nadal wymagają oględzin. Nie przesuwano origin ani parentów.

W tej nowej fixture wszystkie trzy ołówki mają jawne `size={x=14 y=14}`,
a Save/Cancel `size={x=16 y=16}`. Usunięto `scale`; ołówki i Save otrzymały
`buttonFont="hoi_18mbs"`. Pozycje i natywne assety nie zmieniły się. Vanilla
`interface/airselectionview.gui:32–40` potwierdza `buttonType` z jawnym `size`
i `quadTextureSprite`; `tank_designer_view.gui:290–297,1500–1506` potwierdza
font dla Save/notes. Oba assety są `textSpriteType` w `core.gfx:1851–1862`.
Vanilla notes/Save w tych przykładach nie mają `size`, więc hipoteza zerowego
hitboxu nadal wymaga runtime. To kandydat po niewidocznym ołówku w PID43444,
a nie potwierdzona naprawa. Aktywnych plików tego procesu nie zmieniano.
Nie dodano hotspotów nazw ani nowych assetów.

Dokładny manifest znajduje się w `native-contract.json`, a kontrola źródeł,
zakres zmian i hashe w `static-review.json`. Składnia sprawdzona lokalnym parserem
nie oznacza akceptacji parsera HOI4. Nowa fixture nie zalicza prefill, keyboard,
Open/Cancel/draft, menu/load, actual Apply, save/restart ani multiplayer.
`expected-input.json` zachowuje przykładowe kody Jan Żółć z bazowego transportu;
carriery zawsze odczytują rzeczywiste aktualne nazwy, nie ten przykład.

## Revision after PID42200 Exit

The preceding source-only notes describe the original fixture. Its live35/69/70
transport, all five native prefills, draft/hide, Cancel and explicit same-epoch
menu/load passed in PID42200; initial rendering remained blank until focus.
Enter delivery was NOT established: Return produced no diagnostic callback.
No name setter or game save ran. See TENTH-RUN-NOTES and PROGRESS.

This new unloaded revision changes exactly two leader/party background references
to native GFX_generic_bg2 (8px corners). Country has no frame; all geometry, fields,
carriers, helpers and selectors remain unchanged. The separate renderB20 candidate
calls22F4D80 once per opening. Fresh-process pre-focus pixels, black-block removal
and transport regression remain pending; no Enter/focus change is included.
