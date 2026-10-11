# Rename Anything (HOI4)

Mod z oknem do wpisywania nazw własnych postaci, stanów i miast (punktów zwycięstwa),
z eksperymentalną wtyczką natywną do nazwy i przymiotnika kraju.
Interfejs jest po polsku i angielsku; pozostałe języki gry dostają angielskie napisy.

## Stan projektu

- Poprawka nadpisywania decyzji przeszła niezależny test w grze. Pełny restart i wczytanie
  zapisu zachowały nazwę kraju na mapie, w dyplomacji i tooltipie. Poprawiona lista miast
  przeszła nowy test PL: własny Apply zmienił VP362 na „Nowy Gdańsk” na mapie i w panelu
  prowincji. Nazwa przetrwała pełny restart i wczytanie własnego zapisu QA.
  Przycisk przy panelu stanu poprawnie otworzył trzy miasta Gdyni.
  Weryfikacja lidera i finalnego zapisu nadal trwa. Nie jest to gotowe wydanie. Szczegóły i granice
  potwierdzenia są w [raporcie testów](docs/test-report.md) i [handoffie](docs/HANDOFF-20261011.md).
- `mod/` zawiera implementację skryptową i `descriptor.mod`. Generator oraz kontrola referencji
  przechodzą lokalnie; wynik bieżących testów w grze opisuje [raport testów](docs/test-report.md).
- Próby na HOI4 1.19.3.0 potwierdziły przyjmowanie dowolnych literałów przez efekty zmiany nazw
  postaci, stanów i prowincji oraz ich trwałość po zapisie i wczytaniu. To dowód mechanizmu;
  pełny interfejs moda wymaga osobnej weryfikacji opisanej w raporcie.
- **Nazwa i przymiotnik kraju wymagają wtyczki natywnej z `plugin/`.** Zakładka „Kraj” zapisuje
  oba pola w tagu kosmetycznym gry. Bez załadowanej DLL tag pozostaje zapisany, ale gra
  wyświetla oryginalną nazwę. Aktualny zakres potwierdzenia na żywo opisuje raport testów.
  Postacie, stany i miasta korzystają z części skryptowej bez DLL.
- Multiplayer nie został jeszcze potwierdzony na dwóch klientach. Nie traktuj tej wersji jako
  wydania ze zweryfikowaną zgodnością MP.

Dowody wcześniejszych prób: [probe 1](docs/stage0-probe-results.md),
[probe 2](docs/stage0-probe2-results.md). Uzasadnienie ograniczenia nazw krajów i stan badań
natywnych: [naming-internals.md](docs/naming-internals.md).

## Instalacja lokalna

1. Zachowaj cały katalog `mod/` z repozytorium, np.
   `C:/Users/user/Documents/GitHub/hoi4-rename-anything/mod`.
2. W swoim katalogu użytkownika HOI4 (`Documents/Paradox Interactive/Hearts of Iron IV/mod/`)
   utwórz plik `rename_anything_dev.mod` z poniższą zawartością. Dostosuj ścieżkę bezwzględną;
   musi wskazywać na **podkatalog `mod`** zawierający `common/`, `interface/` i `descriptor.mod`.

   ```text
   name="Rename Anything (dev)"
   path="C:/Users/user/Documents/GitHub/hoi4-rename-anything/mod"
   version="0.1.0"
   supported_version="1.19.*"
   ```

3. Dodaj mod do playsetu w launcherze i włącz go. Do odtwarzalnego testu wybierz tylko ten mod.
   Zachowaj własny playset; instalacja nie wymaga podmiany `dlc_load.json` ani plików gry.
4. Uruchom grę i kampanię. Przycisk „Zmień nazwy” / „Rename” jest w lewym górnym rogu.

## Wtyczka do nazw krajów

Źródła, instrukcja budowania oraz użycia są w [plugin/README.md](plugin/README.md).
Wtyczka jest przeznaczona wyłącznie dla przypiętego Windows/Steam HOI4 **1.19.3.0**,
SHA-256 `7DC947BE34970DA1E1C787BCDDBE7F62B610FF258AEBF8F06AA8B348F3A031D5`.
Injector odmawia pracy z innym EXE. Pliki gry i istniejący `steam_api64.dll` nie są podmieniane.

Uruchom grę z modem, a następnie załaduj zbudowaną DLL do właściwego procesu przez
`rename_anything_injector.exe PID ABSOLUTNA_ŚCIEŻKA_DLL`. W zakładce „Kraj” sprawdź napis
**DLL: ACTIVE (RN1)**, wpisz nazwę i przymiotnik, następnie kliknij „Zastosuj”. Oba pola są
wymagane. Napis „Tekst zapisany” potwierdza jedynie zapisanie danych; sprawdź faktyczną nazwę
w grze. **INACTIVE / NIEAKTYWNA oznacza, że zmiana nazwy kraju nie będzie wyświetlana.**

DLL trzeba ponownie załadować po każdym uruchomieniu gry, także przed sprawdzaniem zapisu
z własną nazwą kraju. Nie odłączaj DLL od działającego procesu; zakończ grę, aby ją usunąć.
Nazwa i przymiotnik są przechowywane w zapisie jako tag kosmetyczny, a nie w pliku lokalizacji.
„Przywróć oryginalną nazwę” usuwa bieżący tag; **nie odtwarza wcześniejszego tagu kosmetycznego**
nadawanego np. wydarzeniem lub innym modem.

Przymiotnik jest dostępny w tekstach gry odwołujących się do `GetAdjective`.
Istniejące dosłowne nazwy dywizji, szablonów i partii nie są z niego tworzone:
vanilla POL używa m.in. `Dywizja Piechoty` i `Sanacja`. Mod nie przepisuje tych tekstów.
Nazwy jednostek i szablonów można zmienić osobno w standardowym interfejsie gry;
nazwy partii wymagają osobnej lokalizacji. Ten zakres DoD pozostaje ograniczony.

## Obsługa

- **Postacie:** wybierz własną postać na liście i kliknij „Zmień”. Lista odświeża się po otwarciu
  okna lub zmianie zakładki, a strony mieszczą po 10 pozycji. Zakładka „Kraj” ma też skrót do przywódcy.
- **Stany:** wybierz własny stan i „Zmień”. „Przywróć” usuwa nadpisanie nazwy. Przyciski są też
  w panelu zaznaczonego własnego stanu na mapie.
- **Miasta:** w zakładce „Stany” kliknij „Miasta” obok wybranego stanu albo użyj „Miasta”
  w panelu Rename Anything przy otwartym widoku własnego stanu na mapie. Samo kliknięcie
  mapy nie przełącza listy miast. Następnie zmień nazwę wybranego punktu zwycięstwa.
  Lista pokazuje oryginalne nazwy z lokalizacji, także po zmianie. „Przywróć” usuwa
  nadpisanie nazwy prowincji. Zwykła podpowiedź terenu pokazuje nazwę stanu, nie nazwę miasta.
- **Kraj:** wpisz osobno nazwę i przymiotnik, zatwierdź oba pola i kliknij „Zastosuj”. Wymaga
  aktywnej wtyczki opisanej powyżej. Limit 32 znaków dotyczy każdego pola osobno.
- Pole przyjmuje do **32 znaków**: A–Z / a–z, cyfry, spację, `-`, `.`, apostrof oraz
  `ąćęłńóśźż` i ich wielkie odpowiedniki. Litery, Shift+litera, cyfry, `-`, `.`, Backspace,
  Enter i spacja mają skróty; można też klikać klawiaturę ekranową. Polskie litery i apostrof
  wpisuje się przyciskami; przełącznik wielkich liter obejmuje polskie znaki.
- Skróty gry pozostają aktywne podczas wpisywania: spacja również pauzuje/wznawia grę,
  a inne klawisze mogą otwierać panele gry. W razie kolizji użyj przycisków ekranowych.
- „Anuluj” odrzuca bufor. Zmiana postaci nie ma przycisku przywracania; wpisz wcześniejsze imię
  lub wczytaj wcześniejszy zapis. Nazwy ustawione przez efekty są częścią zapisu gry.

Polskie znaki działają w efektach nazw i w przetestowanych miejscach interfejsu przy języku
angielskim. Pełna czytelność wszystkich fontów i etykiet pozostaje punktem kontroli raportu;
AltGr nie jest wejściem tekstowym tej klawiatury skryptowej.

## Multiplayer, ironman i zgodność

Logika wpisywania oraz zmiany nazw jest wykonywana przez efekty przycisków scripted GUI.
Bufory należą do krajów, a tablice kodów znaków mają identyczną zawartość we wszystkich
lokalizacjach. To założenie synchronizacji, **nie wynik testu MP**. Gracze kooperacyjni tego
samego kraju współdzielą bufor. Do weryfikacji potrzebne są dwa klienty z identyczną wersją
moda i zestawem modów, kontrola nazw u obu graczy, zapis/wczytanie i obserwacja OOS.
Przy zmianach kraju **każdy proces gry musi mieć tę samą aktywną DLL**; zwykła zgodność checksum
modów nie dowodzi załadowania ani zgodności wtyczki. Procedurę i blokady testu na jednej maszynie
opisuje [plan MP](docs/mp-test-plan.md).

Mod zmienia pliki `common/`, więc zmienia checksum gry. Nie jest zgodny z osiągnięciami
wymagającymi niezmienionej checksumy. Obsługi ironman nie zweryfikowano; do testów używaj
kampanii bez ironman i kopii zapisu.

Badana wersja gry to **Windows / Steam, HOI4 1.19.3.0**. Deklaracja `supported_version="1.19.*"`
w deskryptorze ogranicza ostrzeżenia launchera; nie stanowi dowodu działania na innych patchach.
Tabela miast pochodzi z vanilli 1.19.3 (955 stanów z VP, 1500 punktów). Mody zmieniające mapę,
ID stanów/prowincji lub dodające VP wymagają regeneracji tabel i ponownego testu. VP dodane
w trakcie kampanii nie pojawią się automatycznie. Mod nie obejmuje nazw partii politycznych.

## Odinstalowanie

Wyłącz mod w playsecie i usuń `rename_anything_dev.mod` oraz kopię jego katalogu, jeżeli była
utworzona wyłącznie dla niego. Pliki instalacji gry nie są zmieniane. Nazwy postaci, stanów i miast
zapisane w kampanii mogą pozostać po wyłączeniu moda; odinstalowanie nie jest ich cofnięciem.
Przed odinstalowaniem przywróć nazwy stanów/miast w UI albo zachowaj wcześniejszy zapis.
Zmienne moda mogą pozostać w istniejącym zapisie. Kontynuację bez moda trzeba sprawdzić na kopii.
Wtyczkę usuń dopiero po zamknięciu gry. Zapisany tag kraju bez DLL wraca wizualnie do nazwy
oryginalnej, ale nadal jest częścią zapisu; aby go usunąć, przed odinstalowaniem użyj resetu kraju.

## Steam Workshop

`mod/` jest katalogiem zawartości zwykłego moda skryptowego. Repozytorium nie zawiera
opublikowanego identyfikatora Workshop; publikacja wymaga osobnego przesłania przez launcher.
Steam Workshop jako platforma może dystrybuować pliki DLL, ale przyjmowanie ich przez uploader
HOI4 nie zostało przetestowane. Sama subskrypcja nie ładuje obecnej DLL z `plugin/` do gry;
ten komponent wymaga osobnego uruchomienia injectora. Szczegóły i granice ustaleń opisuje
[research dystrybucji natywnej przez Workshop](docs/workshop-native-research.md).

## Development

```powershell
python tools/gen.py
python tools/check.py
```

Generator czyta instalację gry bez jej modyfikowania; inną ścieżkę podaj przez
`python tools/gen.py --game "D:/Steam/steamapps/common/Hearts of Iron IV"` i
`python tools/check.py "D:/Steam/steamapps/common/Hearts of Iron IV"`.
Edytuj generator, nie pliki oznaczone `GENERATED`. `tools/check.py` sprawdza referencje, strukturę
oraz lokalizacje; nie zastępuje parsera gry, testu zapisu/wczytania ani testu multiplayer.

Tymczasowe logi city Apply i `debug = yes` usunięto po potwierdzeniu właściwego celu
i efektu w grze. Dowody diagnostyki zachowano w raporcie testów. Lista miast nadal
pokazuje oryginalne nazwy z lokalizacji.

Skrót Backspace pozostaje aktywny. Mod dostarcza brakującą w vanilli ikonę `GFX_BACKSPACE`
dla automatycznej podpowiedzi skrótu, która wcześniej dodawała błąd `Couldnt find texticon: BACKSPACE`.
Poprawka renderowania podpowiedzi wymaga ponownej kontroli logu po uruchomieniu gry.

`tools/test-session.ps1 -Action Begin -Language polish` przygotowuje lokalną sesję testową
1720×900; `-Action Restore` przywraca oryginały po ich weryfikacji SHA-256. Helper wymaga
zamkniętej gry. Zabezpiecza `dlc_load.json`, `settings.txt` i — jeśli istnieje —
`pdx_settings.txt`: nowsza gra odtwarza ustawienia legacy z tego drugiego formatu, więc
język, rozdzielczość okna i tryb okienkowy trzeba ustawić w obu. Restore obsługuje również
starsze manifesty obejmujące tylko dwa pliki. Do prób helpera używaj tymczasowego
`-UserDirectory`; nie uruchamiaj go na bieżącej konfiguracji podczas pracy gry.
Powtarzalny test obu formatów i starszego manifestu uruchomisz przy zamkniętej grze poleceniem
`powershell.exe -NoProfile -File tools/tests/test-session-fixture.ps1`; używa wyłącznie nowego
katalogu TEMP i pozostawia tam wynik do wglądu.

Struktura: `mod/` — mod skryptowy; `plugin/` — badania komponentu natywnego; `probes/` —
osobne mody eksperymentalne; `docs/` — dowody i raporty; `tools/` — generator i kontrola statyczna.
