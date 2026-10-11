# Nieaktywny kandydat własnego edytora nazw

Ten katalog rozwija zamrożony `rn_inline_editor_apply_qa`. Nie został zarejestrowany
w launcherze ani włączony. Nie zawiera nowej DLL, builda, injectora ani producenta
syntetycznego tekstu. `descriptor.template` wymaga osobnego przygotowania przez root
po review; w tym zadaniu konfiguracja gry pozostaje nietknięta.

Kraj, przymiotnik i aktualny przywódca mogą być edytowane dla własnego kraju gracza,
bez testowego ograniczenia do Polski. Partia oznacza wyłącznie partię aktualnie
rządzącą w jednej z czterech bazowych grup: democratic, communism, fascism,
neutrality. Nie obsługujemy w tym kandydacie opozycji ani własnych grup ideologii.
`player_context` ustanawia kontekst lokalnego gracza; dodatkowe `tag = ROOT`
sprawdza zgodność CURRENT z ROOT. `is_ai = no` jest warunkiem dostępności UI,
sam tag ani ten warunek nie dowodzą uprawnień lokalnego gracza. Multiplayer
i edycja obcego kraju nie są tutaj zaakceptowane.

Pozostają dokładne trzy modele, pięć natywnych pól, nazwy carrierów i selektorów
bridge opisane w [native-contract.json](native-contract.json). Sufiks `neutrality`
w nazwach kontrolek/modelu partii jest zachowanym kluczem protokołu; nie ogranicza
nowego dispatchu do tej grupy. Transport ma nadal 35/69/70 rekordów, świeży
`rn_ip_cmd_epoch` oraz dla kraju świeży `rn_native_cap=1` z wersjonowanej capability.
Enabled nie zależy od tempów dostarczanych dopiero przez konstruktor komendy.
Enter, autofocus i zaznaczanie tekstu zależą od osobno testowanego wariantu native;
te źródła nie dodają ich obsługi.

Open partii wybiera jedną jawną grupę, przypina typed COUNTRY `THIS`, zapisuje
logiczną grupę 1/2/3/4 oraz zwiększa wspólną epokę. Te liczby nie są ID silnika.
Apply ponawia kompletny guard kontekstu, epoki, kraju i zgodności grupy z bieżącym
rządem przed walidacją całej pary oraz po niej. Dopiero wybrana zgodna gałąź
kopiuje oba bufory i wykonuje jeden `meta_effect` z literalnymi short/long oraz
stałą ideologią. Brak zgodności daje error 9, field 0, zachowując draft, flagę,
epokę, piny i bufory. Nie ma ścieżki częściowego zapisu poprawnego A przy błędnym B.
Walidacja przed zapisem nie zapewnia rollbacku w razie awarii samego silnika.

Zmiana rządu blokuje także prefill: nowe warunkowe scripted localisation zwraca
pusty tekst obu carrierów, gdy przypięty kraj/grupa przestały odpowiadać celowi.
Istniejący native decoder odrzuca pusty snapshot; nie dopisujemy fałszywej nazwy.
Wiersz etykiety pokazuje wtedy „Zmieniony cel: Anuluj”, a Cancel pozostaje dostępny.
Powrót rządu do tej samej grupy oznacza ponownie tę logiczną partię; nie przypinamy
historycznej instancji rządu. Po Cancel nowe Open przypina aktualny rząd.

Lider nadal pochodzi z generic `every_character`/`is_country_leader`; nie było
POL-specific character IDs do usunięcia. Nowy czysto tymczasowy guard sprawdza
own aktywnego lidera i typed singleton przed pełną walidacją oraz po niej.
Dopiero później odświeżany jest dotychczasowy roster owned/current i sprawdzana
jednoznaczność. Dotychczasowy literalny `set_character_name`, strict copy oraz
guard charakteru w scope loop pozostają. Żaden helper nie otwiera starego `rn_input`.
Legacy `rn_open`/`rn_input` blokują visible/Open/Apply; Cancel działa niezależnie.

Typografia kraju zmienia wyłącznie dwa fonty pól na `hoi_16mbs` oraz zamkniętą
etykietę na `Arial12`. Geometria pozostaje identyczna, w tym wysokość pola 16 px;
obcięcie tekstu wymaga QA. Fonty pochodzą z vanilla `core.gfx`: hoi_16mbs
1093–1111, Arial12 1733–1753. Rozmiar nazwy zasłoniętej pod polem nie jest
naprawiany lokalnym fałszywym odczytem ani automatycznym zamykaniem polityki.

Partia ma jedno podpisane wspólne miejsce „Partia rządząca”, zamiast ołówka
przypisanego na stałe do czwartego wiersza. Zamknięty launcher jest lokalnie
18,368 / 236×14; ołówek w nim 220,0 / 14×14. Otwarty editor 18,304 / 196×62
tymczasowo nakłada się na read-only informacje o rządzie i ikonę frakcji.
Wspólne pola zachowują lokalne pozycje i wielkości z bazowego fixture. Status
celu używa `Arial12` w dotychczasowym wierszu etykiety, bez powiększenia okna.
To świadomy kompromis szkicu do QA, nie zatwierdzony wygląd produktu.

Primary `interface/countrypoliticsview.gui`: ruling_party_info jest 88,305 /255×60
(95–126), elections kończy się na y366; pie chart zaczyna x270 (75–94).
Manage occupied/subjects/collaborations są na y390 (656–735), więc oba nowe
prostokąty partii kończą się przed nimi. Native informacje mogą wystawać poza
nasz frame; hit testing, warstwy, tooltips i czytelność wymagają zrzutu w grze.
Nie dodajemy hotspotu na samej nazwie ani nowych assetów. Lider zachowuje
154,299 launcher i 18,262 /155×36 editor. Read-only „QA guards” nadal jest
diagnostyką tego kandydata, nie testem tekstu ani elementem docelowego produktu.

W obecnym runtime QA bazowego wariantu GetLeader/GetRulingParty i tooltips
odczytują zapis, lecz natywne wiersze lidera/partii odświeżają się dopiero po
ponownym otwarciu polityki. Native refresh bada osobny agent. Ten kandydat nie
rozwiązuje tego problemu i nie udaje odświeżenia własną kopią tekstu. Dowód
bazowego uruchomienia: [day2-inline-apply-run.json](../../docs/evidence/session-20261011/day2-inline-apply-run.json)
oraz [TWELFTH-RUN-NOTES.md](../../docs/evidence/qa-20261011-day2/TWELFTH-RUN-NOTES.md).
Wcześniejszy dowód literału/serializacji partii neutrality jest osobny:
[day2-party-literal-save-bytes.json](../../docs/evidence/session-20261011/day2-party-literal-save-bytes.json).
Żaden z tych raportów nie zalicza nowych czterech gałęzi ani tej geometrii.

Dozwolony przyszły co-load: **wyłącznie główny dev mod + ten jeden fixture**.
Zabronione jest współwłączenie dowolnego innego probe moda, szczególnie
rn_in_place_ui, rn_country_inline_ui, rn_inline_leader_transport_qa,
rn_inline_leader_apply_qa, rn_inline_editor_transport_qa, rn_inline_editor_apply_qa,
rn_inline_pair_qa i rn_inline_payload_qa: współdzielą modele, helpery lub klucze.
Proces musi używać dokładnie jednego zgodnego wariantu native bridge. Ten katalog
nie zmienia whitelisty ani zasad co-load DLL.

`python probes/rn_inline_editor_product_qa/check.py` wykonuje odczytową kontrolę
AST, hashy i ograniczony istniejący ApplyVM na rzeczywistych nowych źródłach.
Sprawdza wszystkie cztery gałęzie w trzech niepolskich krajach, odrzucenia przed
i po walidacji, cross-product grup/rządów, Cancel po zmianie rządu, capability
kraju, brak kolizji z mod/ i celowo uszkodzone kontrakty wyłącznie w pamięci.
`--write-report` zapisuje tylko lokalny `static-review.json`. Nie uruchamia gry.
Pure single CD171D, pure pair E278DF i sloty RN_PS/RN_PL są kopiami bajt w bajt;
leader i pair Apply są jawnie zmienionymi kandydatami, nie kopiami dawnego runtime.

Przed aktywacją potrzebne są niezależny review i świeże QA własnej kampanii dla
każdej bazowej grupy: prefill obu pól, różne nazwy Unicode, jedno Apply, save/reload;
zmiana grupy przed prefill i przy otwartym drafcie; invalid B; Cancel; granice
player_context; menu/load i draft lifecycle. Statyka nie zalicza parsera HOI4,
działania GUI, setterów, serializacji nowych gałęzi, native focus ani multiplayer.
