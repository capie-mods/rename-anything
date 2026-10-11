# Niewłączony szkic nazwy własnego kraju

Stan 2026-10-11: osobny szkic do przeglądu, bez rejestracji, aktywacji, DLL ani
testu w grze. Realizuje zaakceptowaną propozycję
[drugiego wiersza nagłówka](../../docs/evidence/session-20261011/day2-own-country-inline-proposal.txt).
Nie zmienia `mod/`, `rn_native_input` ani `rn_in_place_ui`.

Pod nagłówkiem polityki widnieje własna nazwa `[ROOT.GetName]` i mały ołówek.
Otwarcie zastępuje ten wiersz dwoma natywnymi `editBoxType`: po lewej nazwą
państwa, po prawej przymiotnikiem. Tooltip ołówka objaśnia oba pola. Obok są
wyłączona ikona Apply i Cancel. To mały szkic przy nazwie, zgodny z
`.impeccable.md` i `docs/in-place-editing-plan.md`.

Pola mają początkowo pusty `text`. Osobne ukryte `instantTextboxType` niosą
`[ROOT.GetName]`, `[ROOT.GetAdjective]` oraz epokę `[?ROOT.rn_ip_epoch|0]` w tym
samym modelu gracza. Nie stanowią automatycznego powiązania z edytorami.
`native-contract.json` podaje dokładne nazwy; obecna whitelist natywna ich nie
obsługuje. Nie zaimplementowano prefill, fokusu, Enter/Escape ani transportu
dwóch pól. Apply ma `always = no`, a jego placeholder wyłącznie loguje.

Oba modele mają `context_type = player_context` i `parent_window_token =
politics_tab`. Dokumentacja ustanawia scope gracza; `tag = POL` i `is_ai = no`
ograniczają jednorazową próbę QA. Nie są docelowym ograniczeniem produktu ani
samodzielnym dowodem własności w multiplayer. Nie korzystamy ze wskazanego kraju
w dyplomacji ani z zaznaczenia mapy.

Open sprawdza w enabled i ponownie w efekcie, że nie ma flag `rn_input`,
`rn_ip_leader_open`, `rn_ip_party_neutrality_open` ani własnej
`rn_ip_country_open`. Ustawia tylko tę ostatnią i zwiększa wspólną `rn_ip_epoch`.
Cancel usuwa tylko własną flagę i również zwiększa epokę. Nie wywołuje cudzych
helperów ani nie zmienia typed pina lidera, bufora Rename czy nazw w grze.

Wspólny niewłączony kandydat `rn_in_place_ui` ma już przygotowane wzajemne
blokady: Open lidera w enabled/helperze oraz kontekst Apply lidera odrzucają
`rn_ip_country_open`; Open partii w enabled/efekcie odrzuca tę flagę i stare
`rn_input`. Dotychczasowe przełączanie lider/partia pozostaje. Nie ma wywołań
cudzych helperów ani zależności od ich obecności przy otwarciu kraju. To nadal
kontrola statyczna; współdziałanie flag wymaga testu przed aktywacją produktu.
Trzeba też ustalić reset flag/epoki przy zamknięciu
polityki, menu/load, zmianie gracza i odbudowie GUI. Skryptowe flagi mogą trafić
do save; nie zakładamy automatycznego anulowania edycji.

Współrzędne są lokalne do `politics_tab`, którego vanilla origin przy otwarciu
to `(-6,78)`, szerokość 550 px. Zamknięty wiersz zaczyna się `(45,29)`; etykieta
ma 365×14, a ołówek jest w `(424,29)` i ma około 14×14. Otwarty root `(45,28)`
ma 405×16: nazwa 210×16 przy x0, przymiotnik 145×16 przy x218, Apply16 przy
x369, Cancel16 przy x389. Kończy się na x450/y44, przed vanilla tłem sekcji
głównej, celem narodowym `(179,48)` i portretem `(18,58)`.

`Main_14` istnieje w tej instalacji i vanilla używa go w etykietach wysokości
14 px. Czy dwie kontrolki wysokości 16 px są czytelne, czy tytuł nie wychodzi
poza swój box oraz czy ikony, clipping i skalowanie pasują wizualnie, wymaga QA.
Nie dodano obramowania zajmującego dodatkowe piksele. Długie nazwy, polskie znaki,
lokalizacje i UI scaling nie zostały ocenione w grze. Gdy wiersz okaże się za
niski, należy wrócić do geometrii nagłówka; nie przesuwać go na cel narodowy.

Primary źródła z `GAME = C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV`:

- `common/scripted_guis/_documentation.md:11,20,29`: scope gracza i token polityki.
- `interface/countrypoliticsview.gui:3-10,27-44,54-71,629-653`: parent, tytuł,
  początek głównego tła, portret/cel narodowy oraz close/rules.
- `documentation/loc_objects_documentation.md:225-227,357-359`: kraj GetName
  i GetAdjective; hidden carrier zawiera samą rozwiązaną nazwę.
- `interface/unitview.gui:362-371,3027-3038`: natywny editBoxType, puste `text`,
  `borderSize` i font. `interface/mapicons.gui:72-79,256-263` używa Main_14;
  `interface/core.gfx:870-883` definiuje ten font.
- `interface/core.gfx:1851-1862`: save/edit-notes, klatki 30×30, skale
  0.533333/0.466667 do około 16/14 px. Cancel jest w
  `interface/general_stuff.gfx:215-219`, przykład `interface/chat.gui:276-284`.

`static-review.json` zawiera inventory, sprawdzone źródła i SHA256. To kontrola
statyczna, bez potwierdzenia parsera gry, natywnego wpisywania, Apply czy zapisu.
