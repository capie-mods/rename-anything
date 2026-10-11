> **WYCOFANY (integracja z mod/, 2026-10-11).** Ten probe definiuje te same modele `rn_ip_*`,
> efekty lub klucze co `mod/` (źródło `tools/inline_editor/`, generator `tools/gen.py`).
> **Nie ładuj go razem z `mod/`**: dałoby to duplikaty definicji albo cofnęło zmiany generatora.
> Zostaje w repo jako historia QA; deskryptor w profilu wyrejestrowuje root.

# Niewłączona próba rzeczywistego Apply lidera

Stan 2026-10-11: osobna kopia `../rn_in_place_ui`, przygotowana wyłącznie do
przeglądu. Nie zarejestrowano descriptoru ani nie zmieniono konfiguracji, DLL,
procesu czy aktywnych fixture. **Nie włączać**, dopóki root nie zakończy obecnej
próby log-only transportu, prefill, Cancel i zachowania draftu oraz niezależnego
review tego kandydata.

Ta próba może rzeczywiście zmienić nazwę aktualnego własnego lidera POL. Nie wolno
ładować jej jednocześnie z `../rn_in_place_ui` ani
`../rn_inline_leader_transport_qa`: mają identyczne nazwy modeli, kontrolek,
scripted effects i lokalizacji. Zależności: główny mod (`RN_B_0..31`) oraz osobny
kandydat `inline_leader_bridge.dll`, którego dokładna whitelist zna model
`rn_ip_leader_gui` i selector `rn_ip_leader_apply_click`. Fixture nie dostarcza
producenta payloadu, syntetycznego tekstu ani hooków. Enter pozostaje diagnostyką
mostka; ta próba nie deklaruje wysyłania Apply przez Enter.

## Zmiana względem kopii bazowej

Jedyny przycisk rzeczywistego Apply to istniejące zatwierdzenie przy liderze.
Jego enabled jest identyczny z log-only transport QA: własny `player_context`,
POL, `is_ai = no`, otwarty lider, brak otwartej partii/kraju i legacy
`rn_open/rn_input`, dodatnia epoka, istniejąca typed identity, singleton pin oraz
aktualny własny władca zgodny z pinem. Enabled celowo nie zależy od payloadu:
engine ocenia go przed injekcją temp records w konstruktorze komendy.

Effect wywołuje niezmieniony `rn_inline_leader_apply`. Helper ponawia kontekst
oraz legacy guards, równość świeżego `temp_var:rn_ip_cmd_epoch` z dodatnią
`rn_ip_epoch`, odświeżenie własnego rosteru i aktualnego władcy, singleton pin
i membership. Dopiero potem wywołuje niezmieniony `rn_inline_copy_payload`,
który waliduje komplet tekstu przed zapisem bufora. Meta-effect rozwija literal
nazwy. Po ścieżce kodu `0` helper zamyka edytor przez Cancel, unieważnia pin,
podnosi epokę i czyści scratch bufor. Odrzucenie nie przechodzi do rename.
Helper lidera i payload są byte-identical z bazą. Payload SHA256:
`CD171D6203BD66DC7905C7C3D0E1A2750C4B8EABAB45F0540D75D3AF2CE10800`.
Root zgłosił 17 PASS deterministycznych prób skryptowych tego payload helpera;
nie stanowi to testu tego GUI, transportu ani rzeczywistego Apply.

Partia pozostaje wyłącznie prefill/Cancel, z Apply `always = no`. Open, Cancel,
leader/party switch, typed pin, epoka, widoczność, nazwy carrierów i geometria
pozostają zgodne z bazą. Ukryte epoki nadal mają `[?ROOT.rn_ip_epoch|0]`.
Przycisk lidera ma osobny tooltip wskazujący rzeczywisty guarded QA Apply.

## Odczyt zaobserwowanego wyniku

SG loguje stan przed helperem i bezpośrednio po nim, bez komunikatu PASS:

- `RN_ILAQA before current_leader=... cmd_epoch=... epoch=... pin_count=...`
- `RN_ILAQA after error=... current_leader=... cmd_epoch=... epoch=... pin_count=...`

`current_leader` to rzeczywisty country `[ROOT.GetLeader]`. Odczyt po helperze
nie używa pina, ponieważ udana ścieżka go czyści. Pole `error` pochodzi z
`temp_var:rn_ip_leader_error`: 7 kontekst/open, 8 epoka, 9 cel, 1/4/5/6 payload,
0 dojście do efektu rename. **Zero nie jest potwierdzeniem zmiany nazwy**.
Akceptacja wymaga porównania dokładnego tekstu z natywnego pola z późniejszym
GetLeader i nazwą pod portretem oraz osobnego przeglądu game/error logów.
Nie logujemy odgadniętego czy stałego oczekiwanego tekstu.

Na obecnym disposable save lider może nazywać się `Jan Żółć`; carrier zawsze
odczytuje rzeczywistą przypiętą postać. Fixture nie wstawia tej nazwy, nie
ustawia żadnego `rn_native_*` ani `rn_ip_cmd_epoch` i nie ma dodatkowych
przycisków zmiany nazwy. Brak/odrzucony mostek ma zostać odrzucony przez sentinel
lub epokę; to wymaga dowodu w docelowym przebiegu.

## Granice

Kandydat nie został załadowany ani przetestowany w grze. Test parsera tego
callera, Unicode/32 znaki, brak/niepoprawny payload, stara epoka, zmiana władcy,
Cancel i dokładne readback pozostają do QA. Dalszy save/load i pełny restart
rzeczywistego Apply również nie są zaliczone. Brak akceptacji menu/load,
zmiany gracza, draftu między zakładkami ani multiplayer.

Wspólny country-open guard jest zachowany, ale nie wymaga ładowania
`rn_country_inline_ui`; jego modele nadal nie należą do whitelist. Własność
wynika z `player_context` i własnego rosteru, nie z samego `is_ai = no`.
`native-contract.json` opisuje dokładne nazwy i granice. `static-review.json`
obejmuje wyłącznie inwentarz, porównanie źródeł i hashe, nie silnikowy parser.


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
