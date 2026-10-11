# Offline kandydat Apply dwóch pól

Nowe, niewłączone źródła do przeglądu root. Nie są podpięte do GUI ani transportu.
Nie zmieniono istniejących helperów, pair/transport QA, głównego moda, native,
konfiguracji ani buildów. Nie ma testu runtime nowych setterów lub guardów.

Generator zapisuje tylko nowe pliki w niewłączonym rn_in_place_ui:

- `common/scripted_effects/rn_inline_pair_apply.txt`
- `common/scripted_localisation/rn_inline_party_buffers.txt`

Skrypty wymagają CURRENT==ROOT==własny COUNTRY z przyszłego `player_context`.
QA ogranicza się do POL/is_ai=no; te dwa triggery same nie dowodzą lokalnej
własności przy dowolnym wywołaniu helpera. Nie używać diplomacy target context
ani wywołań w innym scope. Multiplayer pozostaje odłożony.

## Kontrakt Apply

`rn_inline_pair_apply_country` i `rn_inline_pair_apply_party` najpierw wykonują
pure-temp guard. Wymagają właściwej flagi open i braku rn_open/rn_input,
lidera oraz drugiego inline editora. Dodatnia całkowita `rn_ip_epoch` musi
równać się świeżemu tempowi `rn_ip_cmd_epoch` z tej samej komendy natywnej.
Pin (`rn_ip_country_target` lub `rn_ip_party_target`) ma być singletonem
zawierającym typed COUNTRY THIS, nie liczbą/nazwą/tagiem z UI.

Partia dodatkowo wymaga utrwalonego pina `rn_ip_party_group=4` i aktualnego
`has_government=neutrality`. To jawna bazowa grupa neutrality, nie automatyczne
rozpoznanie custom subtype. Jeśli władza się zmieniła, Apply odrzuca draft.
Nie deklaruje się obsługi wszystkich ideologii.

Kraj wymaga świeżego `temp_var:rn_native_cap=1`. Przyszły natywny producent
musi przed tym konkretnym dispatch sprawdzić wersjonowany eksport
`RNCountryCapabilities()` przez GetProcAddress i bounded SEH; wynik ma być
aktywny dopiero po RNInitialize. Brak/false/błędna wersja ma odrzucać dispatch;
brak natywnego payloadu lub cap daje odrzucenie skryptowe. Obecność modułu,
saved flag ani wcześniejszy status nie zastępuje capability. Ten etap nie
implementuje producenta capability ani statusu UX/GUI enabled.

Po guardzie wywołuje się niezmieniony pure `rn_inline_pair_validate` E278DF…
zależny od strict helpera CD171D…. Oba pola muszą być kompletne i poprawne:
sentinel1, długość1..32 całkowita, aktywne kody całkowite1..84, padding0.
Potem ponawia się CAŁY guard, włącznie z aktualną partią i capability kraju.
Dopiero wewnątrz tej drugiej udanej bramki zaczyna się pierwszy zapis persistent.
Nie ma persistent refresh helpera ani aliasowania starego rn_buf/rn_len.

| Wynik | err | field/bad |
|---|---:|---|
| Kontekst/open/inny editor/legacy | 7 |0/-1|
| Epoka brak/0/ułamek/stale | 8 |0/-1|
| Typed pin lub current neutrality/group4 | 9 |0/-1|
| Brak/niepoprawny fresh country cap |10|0/-1|
| Niepoprawne A/B |1/4/5/6|field1/2, bad ze strict validatora|
| Wejścia przyjęte, wyemitowano setter |0|0/-1|

Wynik jest w tempach `rn_pair_err/field/bad`. Error0 oznacza ścieżkę emisji
settera w skrypcie, nie dowód powodzenia w silniku. Odrzucenie loguje prawdziwe
wartości i zachowuje wszystkie5 buforów, długości, flagi draft/open, epokę,
piny i group. Prywatne scratch tempy mogą się zmienić.

Kraj kopiuje A do `rn_cname/rn_cname_len`, B do `rn_cadj/rn_cadj_len`, po czym
wywołuje dokładnie raz istniejący `rn_apply_country_name`. Ten helper używa
RN_N/RN_J i jednego `set_cosmetic_tag="RN1|name|adj|"`; wymaga country DLL do
odczytu własnej nazwy. Bufory kraju zostają dla starego UI. Ta zależność nie
znika po zapisaniu kosmetycznego taga.

Partia używa osobnych `rn_pshort/rn_pshort_len` i `rn_plong/rn_plong_len`.
Nowe64 sloty `RN_PS_0..31`, `RN_PL_0..31` korzystają wyłącznie z istniejących
`RN_CH_0..84`. Meta_effect rozwiązuje oba32-slotowe wyrażenia z ROOT i emituje
jeden `set_party_name={ideology=neutrality name="literal" long_name="literal"}`.
Alfabet wyklucza znaki sterujące/składnię; nie dodaje się nowych znaków ani
kolizji z RN_N/RN_J. Party buffers pozostają po sukcesie; inne bufory są bez zmian.

Po wyemitowaniu settera zamyka się tylko właściwy editor, czyści jego pin
(oraz party group) i zwiększa wspólną epokę. Atomic oznacza walidację OBU
pól i guardów przed pierwszym zapisem oraz jeden setter obu nazw. Nie obiecuje
rollbacku po crashu, engine exception czy częściowym niepowodzeniu silnika.

## Przyszłe Open/Cancel — nadal niewywoływane

Nowe `rn_inline_pair_open_country/party` są kandydatami do późniejszego wiring.
Open wymaga własnego POL i braku wszystkich legacy/inline open flags, pinując
typed THIS w nowym singletonie. Partia otwiera się tylko przy neutrality i
ustawia group4. Open zwiększa epokę i podnosi właściwy open flag. Nie kopiuje
payloadu ani buforów. Nie może być wywołany z Apply.

`rn_inline_pair_cancel_country/party` wymaga własnego POL z właściwym open flag,
czyści tylko ten flag/pin (partia też group), zwiększa epokę. Może zamknąć swój
editor mimo innego panelu. Nie zmienia nazw ani żadnego bufora. Te świadome
lifecycle zapisy nie są ścieżką odrzucenia Apply i nie wymagają payloadu.
Istniejące GUI Open/Cancel nie wywołują nowych helperów; runtime pin wiring,
carrier epoch i transport wymagają osobnego przeglądu i świeżego procesu.

## Kontrole offline

```powershell
python probes/rn_inline_pair_apply_source/generate.py
python probes/rn_inline_pair_apply_source/check.py
```

Checker wykonuje faktyczny AST źródeł w ograniczonym modelu, używając
niezmienionych single/pair helperów i istniejącego country helpera. Sprawdza
pełną niezmienność stanu po odrzuceniu obu pól i wszystkich guardów, także
guardów zmienionych po walidacji. Write barrier wymaga zakończonej walidacji
obu pól i drugiego guardu przed każdym zapisem persistent. Udane próby
sprawdzają rozdzielenie buforów, A1/B32 i A32/B1, pojedyncze literalne żądanie
settera oraz cleanup. Dodatkowo sprawdza przyszłe Open/Cancel i wszystkie84
kody w każdym z64 slotów lokalizacji wraz z ukrywaniem slotu przez długość.
Mutacja usuwająca drugi guard musi zostać wykryta przed pierwszym zapisem.
Model tylko zapisuje żądania setterów — ich nie wykonuje.

Primary lokalne źródła: vanilla effects_documentation.md meta_effect i
set_party_name (COUNTRY), triggers_documentation.md is_in_array,
common/scripted_effects/CHI_scripted_effects.txt (COUNTRY THIS w typed array),
mod/common/scripted_effects/rename_anything_generated_effects.txt
rn_apply_country_name, tools/gen.py BUFFERS/CHARS. Literalny setter neutrality
i zapis partii były sprawdzane oddzielnie wcześniej; nowe helpery, piny,
rendering RN_PS/RN_PL, error outputs, lifecycle i pełny Apply nadal wymagają
runtime QA. Brak aktywacji i brak zmian aktualnych fixture.
