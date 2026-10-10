# Rename Anything (HOI4)

Mod z oknem do wpisywania nazw własnych postaci, stanów i miast (punktów zwycięstwa),
z eksperymentalną wtyczką natywną do nazwy i przymiotnika kraju.
Interfejs jest po polsku i angielsku; pozostałe języki gry dostają angielskie napisy.

## Stan projektu

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

## Obsługa

- **Postacie:** wybierz własną postać na liście i kliknij „Zmień”. Lista odświeża się po otwarciu
  okna lub zmianie zakładki, a strony mieszczą po 10 pozycji. Zakładka „Kraj” ma też skrót do przywódcy.
- **Stany:** wybierz własny stan i „Zmień”. „Przywróć” usuwa nadpisanie nazwy. Przyciski są też
  w panelu zaznaczonego własnego stanu na mapie.
- **Miasta:** w zakładce „Stany” kliknij „Miasta”, następnie zmień nazwę wybranego punktu
  zwycięstwa. Lista pokazuje oryginalne nazwy z lokalizacji, także po zmianie. „Przywróć” usuwa
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
Natywny komponent z `plugin/` nie jest automatycznie ładowany przez standardowy system modów HOI4;
subskrypcja Workshop sama go nie instaluje ani nie uruchamia.

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

Struktura: `mod/` — mod skryptowy; `plugin/` — badania komponentu natywnego; `probes/` —
osobne mody eksperymentalne; `docs/` — dowody i raporty; `tools/` — generator i kontrola statyczna.
