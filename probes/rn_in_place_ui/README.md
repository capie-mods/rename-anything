# Niewłączony szkic edycji przy obiekcie

Stan 2026-10-11: osobny katalog do przeglądu, bez rejestracji w launcherze,
bez aktywacji i bez testu w grze. Nie zastępuje `mod/` ani `rn_native_input`.
Obecne hooki znają wyłącznie `rn_native_probe_gui`; ten szkic ich nie rozszerza.

Kierunek z `.impeccable.md` i `docs/in-place-editing-plan.md`: dyskretny przycisk
przy istniejącej nazwie otwiera małe natywne pole w tym samym miejscu. Przyciski
korzystają z podstawowych grafik i fontów HOI4. Nie ma dodatkowego bocznego panelu
ani klawiatury ekranowej. POL/neutrality to ograniczenie jednorazowej próby QA,
nie planowane ograniczenie produktu.

## Co jest przygotowane

- Mały przycisk obok nazwy przywódcy, pod portretem. Edytor zastępuje ten fragment
  nazwy i mieści pole, ikonę zatwierdzenia oraz krzyżyk anulowania.
- Mały przycisk obok czwartego wiersza partii w znanym układzie vanilla POL.
  Pierwsze pole leży przy krótkiej nazwie; drugie, osobne pole pełnej nazwy rozwija
  się bezpośrednio poniżej. Oba należą do tej samej partii neutralnej.
- Trzy prawdziwe `editBoxType` z pustym początkowym `text`. Osobne ukryte
  `instantTextboxType` niosą `[?ROOT.rn_ip_leader_identity.GetName]`,
  `[ROOT.GetRulingParty]` i `[ROOT.GetRulingPartyLong]` w tym samym modelu/kontekście
  co dane pole. Przywódca jest konkretną typed character przypiętą podczas Open.
- Osobne modele launchera i edytora: otwarcie/Cancel zmieniają widoczność korzenia,
  zamiast tylko chować dziecko stale widocznego modelu. Ukryty carrier epoki
  `[?ROOT.rn_ip_epoch|0]` rozróżnia kolejne otwarcia. Odczyt dokładnego formatu
  całkowitego przez DLL wymaga jeszcze testu w grze.
- Przyciski otwarcia i Cancel zmieniają izolowane flagi/typed pin `rn_ip_*`
  oraz `rn_ip_epoch`. Apply jest jawnie wyłączony (`always = no`). Przycisk lidera
  wskazuje niewłączony kandydat helpera; partia ma wyłącznie logujący placeholder.
  Nie przypisano skrótów klawiatury.

Pola **nie są jeszcze wypełniane** zawartością carrierów. Ich związek opisuje
`native-contract.json`, a nie działający mostek. Wpisywanie, prefill, fokus,
Enter/Escape, rzeczywiste Apply, reset bufora przy Cancel i save/load nie są
zaliczone. Nowych modeli nie wolno automatycznie dopisać do filtrów obecnej DLL.

## Kontekst i granice własności

Primary `GAME/common/scripted_guis/_documentation.md:11,20` mówi, że
`player_context` ma scope gracza; `politics_tab` jest jawnym tokenem parenta
na linii 29. Każdy model tutaj ma ten kontekst i parent. Warunek `tag = POL`
wybiera własną kampanię QA, a `is_ai = no` blokuje kraj AI. Ten drugi warunek sam
nie ustanawia lokalnego właściciela ani bezpieczeństwa w multiplayer.
Próba partii dodatkowo wymaga `has_government = neutrality` w visible,
open/enabled i Cancel. Efekty pozostają w country CURRENT ustalonym przez model;
nie przechodzą do kraju wskazanego w dyplomacji ani do bieżącego zaznaczenia mapy.

Kandydat `rn_inline_leader.txt` przy Open zbiera własne postacie i wymaga dokładnie
jednej spełniającej `is_country_leader = yes`. Kopiuje typed scope do osobnej
`rn_ip_leader_target` (singleton) i `rn_ip_leader_identity`. Apply ponownie odświeża
własny roster oraz listę kandydatów, sprawdza zgodność pina, pojedynczego celu
i `is_country_leader` przed pierwszym zapisem bufora. Celowana analiza natywna
potwierdza wybór aktualnego władcy, tą samą ścieżką co GetLeader; osobny guard
własnego rosteru pozostaje konieczny. Open i Apply nadal odrzucają wieloznaczność,
a cały przepływ typed pina wymaga QA w grze.
Sam GetLeader string nie był używany jako tożsamość. Model partii wciąż nie ma
pina ani helpera Apply; wymaga kraj+ideologia+epoka i ponownej walidacji.

Kandydat lidera blokuje równoczesne stare `rn_input`, wymaga świeżego payloadu
z 34 tempvarami helpera root oraz osobnej zwykłej `rn_ip_cmd_epoch` równej
dodatniej bieżącej `rn_ip_epoch`. Klucz epoki ma dokładnie 15 bajtów ASCII, mieści
się w SSO obecnego kandydata bridge. Producent musi kopiować ją z tego samego
świeżego opening/snapshot, sanitize dokładny klucz i sprawdzić overflow fixed-point.
Nie wolno pobierać epoki dopiero przy późniejszym wysłaniu starego tekstu.
Aktualny prefill-only prototype nie produkuje tej komendy ani payloadu.
Parser `temp_var:` w dokładnych callerach jest nadal otwarty.

Po pełnym target/epoch preflight `rn_inline_copy_payload` root rewaliduje cały tekst
i dopiero wtedy kopiuje `rn_buf/rn_len`; helper lidera stosuje dotychczasowy wzorzec
meta_effect plain literal, bez `rn_open_input`, `rn_ttype` ani wspólnych targetów.
Odrzucenie pozostawia pin, flagę, bufor i nazwę; refresh dotyczy tylko dwóch
prywatnych list diagnostycznych. Po ścieżce poprawnego efektu Cancel unieważnia pin
i epokę, a scratch bufor jest czyszczony. Wynik zero to dojście do efektu, nie
potwierdzone działanie GUI/zmiana nazwy. Apply pozostaje disabled do osobnego
review i transport/runtime proof. `rn_ip_epoch` sam nie dowodzi świeżości natywnego
odczytu ani poprawnej obsługi restartu/save/load.

Obie flagi otwarcia są wzajemnie wykluczane. Trzeba jeszcze określić reset przy
zamknięciu polityki, menu/load, zmianie gracza i odbudowie GUI. Flagi/epoka są
zwykłym stanem skryptowym kraju, więc nie należy zakładać automatycznego resetu.
Native integration ma rozwiązywać kontrolki świeżo, bez zachowywania wskaźników
widgetów albo pożyczonych stringów. Pre-fill ma wystąpić raz przy nowym otwarciu;
żaden tick nie może nadpisywać draftu użytkownika.

## Geometria do kontroli na żywo

Współrzędne poniżej są lokalne do głównego `countrypoliticsview` (550 px szerokości),
nie do ekranu. Parent animuje swój origin: vanilla plik ma `show_position=(-6,78)`.

| Element | x,y | w,h | Powiązanie vanilla |
|---|---|---|---|
| Przycisk przywódcy | 177,273 | 14,14 | obok `leader_name` 18,262 / 155x36 |
| Otwarty edytor przywódcy | 18,262 | 178,36 | pod portretem, pole 130x20 |
| Przycisk partii neutralnej | 536,352 | 14,14 | za prawym końcem nazwy x535 |
| Otwarty edytor partii | 354,352 | 196,62 | short 138x18, long 176x18 poniżej |

Partie: `chart_explanation=(18,116)` + `parties_grid=(260,184)` +
`name=(82,4)` daje pierwszą nazwę `(360,304)`. Slot ma 16 px wysokości,
a więc znany czwarty wiersz zaczyna się na y352. Root QA zaobserwował kolejność
vanilla: demokratyczna, komunistyczna, faszystowska, neutralna. Nie jest to dowód
mapowania niestandardowych ideologii. Rozwinięcie partii kończy się na y414,
przed `ideas` na y425; mała wysokość wierszy, hitboxy ikon, border, clipping,
kolejność rysowania i skalowanie UI nadal wymagają oględzin w grze.

Nie dodano kraju w dyplomacji. Dokładna geometria jest znana, a dokumentacja
opisuje `diplomacy_target_context` jako wskazany kraj, ale osobny dowód guardu
lokalnego własnego celu jest konieczny przed przygotowaniem działającego UI.
Sam `is_ai = no` dopuściłby także cudze kraje graczy.

## Primary źródła dokładnej instalacji 1.19.3

`GAME = C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV`.

- `interface/countrypoliticsview.gui:3-10,54-71,584-593,1123-1163`: parent,
  rozmiar, pozycja lidera i złożona geometria wierszy partii.
- `interface/unitview.gui:362-371,3027-3038`: natywny editBoxType, puste `text`,
  font i border. `countryarmyview.gui:269-276` daje dalszy przykład.
- `documentation/loc_objects_documentation.md:189-191,281-283,401-403`:
  GetLeader, GetRulingParty i GetRulingPartyLong w COUNTRY.
- Ten sam plik: GetNeutralParty217-219, GetCommunistParty245-247,
  GetDemocraticParty249-251, GetFascistParty393-395. Vanilla używa wszystkich
  czterech w `localisation/english/aat_decisions_l_english.yml:179-182`.
  Nie odkryto generycznego GetPartyName ani getterów long dla dowolnej ideologii;
  tego zakresu nie zastępują znane gettery czterech podstawowych grup.
- `interface/core.gfx:1851-1862`: vanilla save/edit-notes sprites. DDS mają
  120x30 i 4 klatki, czyli 30x30 na ikonę; scale0.466667 daje 14 px,
  scale0.533333 daje 16 px. `tank_designer_view.gui:1500-1506` używa edit-notes.
- `interface/core.gfx:222,1094,1122,1174`: istniejący border oraz fonty
  `hoi_16mbs`, `hoi_18`, `hoi_18mbs`.
- `interface/general_stuff.gfx:215-219` i `interface/chat.gui:276-284`:
  przycisk Cancel `GFX_closebutton_16`, istniejący DDS16x16.
- `documentation/triggers_documentation.md:3640-3652,5408-5414`: kryteria
  has_country_leader oraz CHARACTER is_country_leader. Dodatkowy bounded native
  proof aktywnego władcy i party serializer: `../../docs/evidence/session-20261011/day2-leader-party-native-review.txt`.

Dowody natywnego odczytu/SetText i otwarte lifecycle:
`../../docs/evidence/session-20261011/day2-native-prefill-static-review.txt`.
Rzeczywisty party Apply ma rozwijać osobne short/long bufory do plain literal
przez meta_effect, analogicznie do aktualnego `tools/gen.py:305-359`, zachować
niezmienioną drugą nazwę i skorzystać ze zwykłej komendy. Wspólny dynamiczny
localisation key nie jest substytutem zapisu dwóch nazw. Szkic partii nie dodaje takiego efektu. Kandydat efektu lidera opisany powyżej pozostaje niewłączony.

## Odbiór przed podłączeniem

Najpierw source/parser/layout review po zamknięciu dotychczasowej gry. Następnie
osobne świadome aktywowanie disposable fixture przez root, native prefill/fokus
bez rename, Cancel/reopen/zmiana celu, potem pełne payload validation i pin-target
Apply. Krótka/długa nazwa partii i trwałość wymagają osobnej próby literal/save.
Aktualna DLL, aktywne pliki moda, config launchera i procesy nie zostały zmienione.
