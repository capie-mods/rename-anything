> **WYCOFANY (integracja z mod/, 2026-10-11).** Ten probe definiuje te same modele `rn_ip_*`,
> efekty lub klucze co `mod/` (źródło `tools/inline_editor/`, generator `tools/gen.py`).
> **Nie ładuj go razem z `mod/`**: dałoby to duplikaty definicji albo cofnęło zmiany generatora.
> Zostaje w repo jako historia QA; deskryptor w profilu wyrejestrowuje root.

# Niewłączony kandydat rzeczywistych Apply — trzy edytory

Stan 2026-10-11: osobna fixture źródłowa, bez aktywacji, konfiguracji,
kompilacji, procesów, UI ani commitu. Aktywny unified, główny mod i build output
pozostały nietknięte. To kandydat do przyszłego disposable own POL QA.

Przed jakimkolwiek runtime Apply root wymaga PASS na unified dla Open,
rzeczywistych prefills, pełnego transportu35/69/70, draft/focus, Cancel oraz
tab/menu-load. Potem wymagane są niezależny source review i świeży proces.
Te pliki nie zaliczają żadnego z tych punktów.

Ładować dokładnie dwa mody: development Rename Anything (mod/) oraz
Rename Anything inline real Apply QA (temporary). Wykluczone są unified
transport i wszystkie pozostałe inline/payload/pair fixture z listy
co_load_exclusions w native-contract.json. Zewnętrzne komponenty przyszłej
próby: główny country DLL z aktywnym versioned RNCountryCapabilities oraz
wyłącznie nowy inline_editor_bridge DLL; bez starszych observer/editor/prefill/
leader bridges. Root ustali ich dokładne zbudowane hashe. Nic ich tu nie ładuje.

## Wiring oraz guardy

Nazwy siedmiu modeli, pięciu native pól, hidden carriers, epoki |0, wszystkie
pozycje, rozmiary14/16 px i fonty są odziedziczone z unified. Brak nowych hitboxów
nazw i assetów. Zmiany GUI poza komentarzem to tooltip rzeczywistego
Apply oraz dwa istniejące tła opisane poniżej. QA guards pozostaje tylko obserwacją flag, poza native whitelist.

Lider używa byte-identical rn_inline_leader.txt z leader_apply_qa. Enabled
wymaga własnego aktualnego lidera i jego singleton typed pina oraz dodatniej
epoki; nie zależy od payloadu przed ctor. Helper sprawdza własny roster/rulera,
command epoch i pełne wejście przed buforem/literalnym set_character_name.

Partia/kraj używają byte-identical rn_inline_pair_apply.txt i
rn_inline_party_buffers.txt z niewłączonego rn_in_place_ui po cleanup56a6873.
Open/Cancel wywołują właściwe rn_inline_pair_open_*/cancel_*. Open pinuje
typed THIS COUNTRY singleton, podnosi epokę i flagę; partia też group4.
Open partii odrzuca otwartego lidera — najpierw Cancel. Lider zachowuje
oryginalny Open, który może wyłączyć flagę partii; pozostający wtedy party pin
jest nieaktywny, a następny Open partii go zastępuje.

Pair Apply enabled sprawdza własny POL/open/no other inline or legacy flag,
epoch>0 oraz singleton typed THIS pin. Partia dodatkowo wymaga current neutrality
i group4. Enabled nie sprawdza ctor-injected payloadu, command epoch ani cap.
Efekt ponawia komplet własnego guardu, sprawdza oba kompletne pola, następnie
ponawia cały guard przed pierwszym persistent write. Kraj wymaga fresh
rn_native_cap=1; bridge w tym samym wykonaniu dwukrotnie pyta dokładne versioned
RNCountryCapabilities (0x524e4301), a brak/zero/inna wersja blokuje dispatch.
Saved flags/status nie zastępują tej capability.

Partia ustawia krótki i długi literal jednym set_party_name z ideology=neutrality.
Kraj kopiuje oba pola do rn_cname/rn_cadj i deleguje jeden rn_apply_country_name.
Nie rozszerzamy wyboru ideologii/subtype. Atomic oznacza walidację obu pól
i guardów przed zapisami, a nie rollback po crashu/engine failure.
Strict CD171D i pure pair E278DF pozostają byte-identical.

Po zmianie rządu editor partii nadal jest widoczny przy own POL/open i braku
legacy flags. Cancel enabled nie wymaga neutrality. Open/Apply nadal wymagają
neutrality/group4/pina, więc odrzucony draft można zamknąć bez zapisu.
Cancel nie wymaga payloadu, epoki komendy ani cap.

## Obserwacje

Każdy SG Apply ma wyłącznie log before, jedno wywołanie sprawdzonego helpera,
log after. Prefix RN_IEAQA obejmuje rzeczywiste ROOT.GetLeader,
ROOT.GetRulingParty/GetRulingPartyLong lub ROOT.GetName/GetAdjective, epoki,
pin count, party group albo cap. Log after podaje aktualny rn_ip_leader_error
lub rn_pair_err/field/bad. Nie ma PASS ani założenia, że error0 dowodzi
widocznej nazwy lub zapisu. Rzeczywisty readback, tooltipy i save/restart
wymagają osobnego runtime QA. Nie ma syntetycznych tekstów/payloadów,
auto-Apply ani Enter dispatch.

Leader error1/4/5/6 oznacza payload,7 context/open,8 epoch,9 target.
Pair payload1/4/5/6 wskazuje field1/2; context7,epoch8,pin/group9,cap10 mają
field0. Te wartości opisują ścieżkę helpera, nie niezależny wynik silnika.
Open/Cancel zmieniają wyłącznie lifecycle; rzeczywisty Apply może zmieniać
bufory/nazwy i zamknąć swój editor po przejściu walidacji.

Dokładny kontrakt oraz hashe źródeł są w native-contract.json i static-review.json.
Lokalny parser/statyka nie zastępuje parsera HOI4. expected-input.json to
odziedziczony przykład obserwacji Jan Żółć, nigdy wstawiany jako tekst pola.

## Małe tło edytorów — hipoteza do retestu

Wyłącznie w tym niewłączonym kandydacie DWIE istniejące background references
lidera/partii zmieniono z GFX_tiled_window_1b_border na GFX_generic_bg2. Country
editor405×16 nie miał tła ani w unified, ani w kandydacie; nie dodano nowego.
Vanilla core.gfx:221–227 ma dla starego assetu border64×64;
countryproductionlineview.gfx:163–168 definiuje nowy asset356×35 z border8×8.
Native resources row w countryproductionlineview.gui:1121–1130 używa go jako
tła okna462×35. Oryginalny DDS obejrzany w pamięci bez zapisu assetów ma
dyskretny ciemny pasek i cienki wklęsły obrys, bez dużych metalowych rogów.

Wysokości36/62/16 i wszystkie pozycje/pola/carriery/buttony zachowano. Rogi8 px
mieszczą się w istniejących oknach lidera/partii. Wygląd, clipping, z-order
i usunięcie czarnych bloków nadal wymagają runtime. To nie jest potwierdzona
naprawa. Osobny native refresh22F4D80 dotyczy układu tekstu przed fokusem.

background-only-transfer.patch zawiera wyłącznie te DWIE zamiany w frozen
unified. Root może przenieść je dopiero PO Exit PID42200 i uruchomić świeżą próbę;
patch nie przenosi real Apply, tooltipów ani jakichkolwiek helperów. W tej pracy
unified, mod/, build outputs, config, procesy i UI pozostały nietknięte.
