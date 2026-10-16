---
description: Jak krok po kroku zainstalować Rename Anything i CAPIE na Windows, jak sprawdzić, czy CAPIE działa, i co zrobić, gdy gra pokazuje „Brak CAPIE”.
---

# Instalacja

Rename Anything potrzebuje trzech rzeczy. Większość problemów bierze się z braku jednej z nich:

| Część | Co to jest | Skąd ją wziąć |
|---|---|---|
| **Rename Anything** | sam mod | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3819937546) |
| **CAPIE** (mod) | mały mod-przełącznik bez zawartości gry; mówi CAPIE, żeby się załadowało | [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3819929471) |
| **CAPIE** (program) | część natywna, dzięki której mod czyta pole tekstowe, zmienia nazwy krajów i flagi | instalowana raz narzędziem w PowerShell |

Sama subskrypcja dwóch modów nie wystarczy. Bez programu mod pokazuje **„Brak CAPIE”** i działają
tylko funkcje bez CAPIE (stany, miasta, postacie).

## Zanim zaczniesz

- Windows 10 lub 11. CAPIE działa tylko na Windows. Na macOS i Linuksie mod działa bez CAPIE
  (zobacz [Bez CAPIE](#without-capie)).
- Hearts of Iron IV 1.19.3.0 ze Steam. Wersję widać w lewym dolnym rogu menu głównego. CAPIE 1.5.0
  obsługuje tylko tę wersję; na każdej innej gra uruchamia się bez CAPIE. Kopie z innych sklepów
  mają inny `hoi4.exe` i nie są obsługiwane.
- Brak lokalnej kopii Rename Anything albo CAPIE w `Dokumenty\Paradox Interactive\Hearts of Iron IV\mod`
  o tej samej nazwie co przedmiot z Workshopu. Przy dwóch modach o tej samej nazwie gra bierze
  lokalny i pomija ten z Workshopu.
- Około 5 minut.

## Krok 1: zasubskrybuj oba mody

1. Zasubskrybuj **[Rename Anything](https://steamcommunity.com/sharedfiles/filedetails/?id=3819937546)** w Steam Workshop.
2. Zasubskrybuj **[CAPIE](https://steamcommunity.com/sharedfiles/filedetails/?id=3819929471)**.
3. Poczekaj, aż Steam pobierze oba (Steam, Widok, Pobieranie).

## Krok 2: zainstaluj program CAPIE

Narzędzie instalacyjne zmienia opcje uruchamiania Hearts of Iron IV w Steam. Steam trzyma je w
pliku, który nadpisuje w trakcie działania, więc w tym kroku **Steam musi być zamknięty**.
Narzędzie może samo zamknąć Steam i potem uruchomić go ponownie.

### Sposób A: jedna linia w PowerShell (zalecany)

1. Naciśnij ++win++, wpisz `PowerShell` i otwórz **Windows PowerShell**. Nie trzeba „Uruchom jako
   administrator”.
2. Wklej tę linię i naciśnij ++enter++:

    ```powershell
    irm https://github.com/capie-mods/capie/releases/latest/download/install.ps1 | iex
    ```

3. Otworzy się menu. Wybierz **1 Install or update** klawiszem ++enter++.
4. Odpowiedz na pytania (instalator jest po angielsku):

    | Pytanie | Odpowiedź |
    |---|---|
    | Install or update CAPIE in `...\RenameAnything`? | ++enter++ (tak) |
    | Loading method: 1 = CAPIE launcher, 2 = proxy | ++enter++ (1, launcher) |
    | Add the CAPIE launcher to the HOI4 Steam launch options? | ++enter++ (tak) |
    | Steam is running. Close Steam now? | ++enter++ (tak) |
    | Several Steam accounts found | numer konta, na którym grasz, albo `A` dla wszystkich |
    | Start Steam again? | ++enter++ (tak) |

5. Poczekaj na **Summary**. Powinno być tam, że CAPIE jest zainstalowane i że Steam je uruchamia
   („started by Steam”). Jeśli któryś krok się nie udał, podsumowanie podaje plik logu; zobacz
   [Jeśli nie działa](#troubleshooting).

Narzędzie instaluje się do `%LOCALAPPDATA%\RenameAnything`. Folderu gry nie zmienia.

!!! note "Co robi `irm | iex`"

    Pobiera skrypt instalacyjny z najnowszego wydania CAPIE na GitHubie i od razu go uruchamia,
    z Twoimi uprawnieniami. Wszystko, co skrypt pobiera potem, jest sprawdzane podpisanym
    manifestem i skrótami SHA-256, ale samego skryptu nic nie sprawdza przed uruchomieniem. Jeśli
    chcesz go najpierw przeczytać, użyj sposobu B.

### Sposób B: pobierz pliki sam

1. Otwórz [najnowsze wydanie CAPIE](https://github.com/capie-mods/capie/releases/latest) i pobierz
   do jednego folderu (np. `Pobrane\CAPIE`): `CAPIE-1.5.0-win64.zip`, `install.ps1`,
   `release-manifest.json` i `release-manifest.json.sig`. Nie rozpakowuj ZIP-a.
2. Otwórz ten folder w Eksploratorze plików, kliknij pasek adresu, wpisz `powershell` i naciśnij
   ++enter++. PowerShell otworzy się w tym folderze.
3. Uruchom:

    ```powershell
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -Install -SteamLaunchOption -PackagePath .\CAPIE-1.5.0-win64.zip
    ```

4. Tutaj pytania są zwykłym tekstem. Na pytanie „Add the selected loading method to the HOI4
   Steam launch options? [y/N]” wpisz `y` i naciśnij ++enter++ (sam ++enter++ znaczy „nie”). Na
   pytania o Steam odpowiedz jak w sposobie A.

## Krok 3: włącz oba mody w zestawie modów

1. Uruchom grę ze Steam (**Graj**). Otworzy się Paradox Launcher.
2. Otwórz **zestawy modów** (Playsets) i włącz **Rename Anything** oraz **CAPIE** w zestawie, z
   którym grasz. Kolejność nie ma znaczenia.
3. Zamknij Paradox Launcher.

Mod CAPIE jest włącznikiem: CAPIE ładuje się tylko wtedy, gdy mod CAPIE jest włączony w zestawie,
z którym uruchamiasz grę.

## Krok 4: uruchom grę we właściwy sposób

1. Uruchom grę przyciskiem **Graj w Steam**. To uruchamia launcher CAPIE, który jak zwykle otwiera
   Paradox Launcher.
2. W Paradox Launcherze wybierz zestaw z oboma modami i naciśnij **Graj**.
3. Odczekaj w menu głównym około **20 sekund** od jego pojawienia się. CAPIE ładuje się dopiero,
   gdy menu główne jest gotowe.

!!! warning "Przy takim starcie CAPIE się nie ładuje"

    - Graj w Paradox Launcherze, który był **już otwarty**, zanim nacisnąłeś Graj w Steam. Najpierw
      zamknij Paradox Launcher całkowicie.
    - Własny skrót gry na pulpicie, skrót do `dowser.exe` albo `hoi4.exe`, albo start gry z
      biblioteki Paradox Launchera.

## Krok 5: sprawdź, czy CAPIE działa

1. Gdy mod CAPIE jest włączony, w menu głównym widać znak CAPIE. Jego podpowiedź mówi tylko, że
   przełącznik jest włączony; nie oznacza, że CAPIE się załadowało.
2. Rozpocznij albo wczytaj grę. Otwórz **Decyzje**, znajdź kategorię Rename Anything i weź
   **Zmień nazwy postaci** (Rename characters). Otworzy się edytor nazw; przejdź na zakładkę
   **Kraj** (Country).
3. Linia przy dole tej zakładki pokazuje **CAPIE 1.5 załadowane**, gdy CAPIE działa. **Brak CAPIE:
   wymaga go Rename Anything** znaczy, że się nie załadowało; przejdź do
   [Jeśli nie działa](#troubleshooting). Z działającym CAPIE widać też ołówki przy nazwie kraju i
   przywódcy w panelu Polityka.

## Jeśli nie działa { #troubleshooting }

### Najpierw: przeczytaj log launchera

Wszystko, co postanawia launcher CAPIE, trafia do `%LOCALAPPDATA%\RenameAnything\launcher.log`.
Naciśnij ++win+r++, wklej `%LOCALAPPDATA%\RenameAnything`, naciśnij ++enter++ i otwórz
`launcher.log`. Czytaj linie z ostatniego startu:

| Linia w logu | Znaczenie | Co zrobić |
|---|---|---|
| Brak nowych linii albo brak pliku `launcher.log` | gra nie została uruchomiona przez launcher CAPIE | sprawdź opcję uruchamiania w Steam (niżej) i uruchom przez Graj w Steam |
| `playset disabled: CAPIE mod not enabled in the playset` | mod CAPIE był wyłączony w zestawie, z którym grasz | włącz mod CAPIE (krok 3) |
| `playset unknown: ...` | nie dało się odczytać `dlc_load.json` | uruchom raz grę z Paradox Launchera ze swoim zestawem i spróbuj ponownie |
| `game ... sha256=...` jako ostrzeżenie i komunikat „not supported” | Twoja wersja gry to nie 1.19.3.0 ze Steam | zobacz [Zła wersja gry](#wrong-version) |
| `bundle check failed` | pliki CAPIE są uszkodzone albo zmienione (często przez antywirusa) | uruchom instalator ponownie i wybierz Install or update |
| `no game appeared in the started tree in time` | grę uruchomił inny, wcześniej otwarty Paradox Launcher | zamknij Paradox Launcher i naciśnij Graj w Steam |
| `CAPIE loaded into pid=...` | CAPIE działa | jeśli mod dalej pokazuje brak, odczekaj 20 s w menu głównym i otwórz edytor ponownie |

### „Brak CAPIE”, choć oba mody są włączone

Sprawdzaj po kolei i testuj po każdym punkcie:

1. Sprawdź opcję uruchamiania w Steam: Steam, Biblioteka, prawy przycisk na Hearts of Iron IV,
   Właściwości, Ogólne, **Opcje uruchamiania**. Musi tam być
   `"...\RenameAnything\current\RenameAnythingLauncher.exe" %command%`. Jeśli pole jest puste,
   instalator nie mógł go zmienić, bo Steam działał: zamknij Steam całkowicie (menu Steam,
   **Wyjdź**, a nie X okna), uruchom instalator ponownie, wybierz **1 Install or update** i
   odpowiedz „tak” na pytania o Steam.
2. Jeśli masz kilka kont Steam: opcja uruchamiania jest osobna dla każdego konta. Uruchom
   instalator ponownie i wybierz konto, na którym grasz (albo `A`).
3. Zamknij każde okno Paradox Launchera, także to w zasobniku przy zegarze, a potem naciśnij Graj
   w Steam.
4. Odczekaj 20 sekund w menu głównym, zanim wczytasz grę.
5. Poszukaj lokalnej kopii któregoś z modów w `Dokumenty\Paradox Interactive\Hearts of Iron IV\mod`
   i usuń ją albo zmień jej nazwę w jej `descriptor.mod`.
6. Sprawdź antywirusa. Niektóre antywirusy blokują CAPIE albo przenoszą je do kwarantanny, bo
   ładuje się do procesu gry. Poszukaj w historii antywirusa plików `RenameAnythingLauncher.exe`,
   `capie_core.dll`, `capie_editor.dll` albo `capie_injector.exe`, przywróć je, dodaj
   `%LOCALAPPDATA%\RenameAnything` do wyjątków i uruchom instalator ponownie.
7. Jeśli nic z tego nie pomaga, użyj [metody alternatywnej](#proxy).

### Instalator nie proponuje zmiany opcji uruchamiania

- Krok Steam potrzebuje instalacji Steam, którą narzędzie znajdzie. Jeśli Steam jest w
  nietypowym miejscu, uruchom sposób B z `-SteamRoot "D:\Ścieżka\Do\Steam"`.
- Jeśli odpowiedziałeś „nie” albo Steam nie zamknął się w 60 sekund, krok został pominięty.
  Zamknij Steam sam (menu Steam, Wyjdź) i uruchom instalator ponownie.
- Możesz też wpisać to ręcznie: w Opcjach uruchamiania wpisz linię podaną wyżej, z pełną ścieżką
  do `RenameAnythingLauncher.exe` w `%LOCALAPPDATA%\RenameAnything\current`, a po niej
  ` %command%`.

### Błędy PowerShell

- „Running scripts is disabled on this system” znaczy, że uruchomiłeś `.\install.ps1`
  bezpośrednio. Użyj linii `powershell -ExecutionPolicy Bypass -File .\install.ps1 ...` ze
  sposobu B albo sposobu A.
- Jeśli Windows blokuje pobrany plik, uruchom w tym samym folderze `Unblock-File .\install.ps1`
  i spróbuj ponownie.
- „irm is not recognized” znaczy, że jesteś w starym Wierszu polecenia (`cmd`), a nie w
  PowerShell. Otwórz Windows PowerShell jak w kroku 2.
- Jeśli sprawdzenie podpisu albo skrótu się nie udaje, pobieranie było niepełne albo plik się
  zmienił. Usuń pliki, pobierz je ponownie i nie mieszaj plików z różnych wydań.

### Zła wersja gry { #wrong-version }

CAPIE 1.5.0 działa tylko z Hearts of Iron IV 1.19.3.0 ze Steam. Na każdej innej wersji, także na
gałęzi beta, gra uruchamia się bez CAPIE, a funkcje bez CAPIE dalej działają. W Steam,
Właściwości, **Wersje beta**, wybierz „Brak”. Żółte ostrzeżenie „not supported” na liście modów
w Paradox Launcherze porównuje `supported_version` moda z wersją gry i samo niczego nie blokuje;
liczy się wersja w menu głównym.

### Metoda alternatywna: loader proxy { #proxy }

Jeśli metoda z launcherem u Ciebie nie działa, CAPIE może ładować plik `version.dll` obok
`hoi4.exe`. Ta metoda dodaje jeden plik do folderu gry, nie potrzebuje opcji uruchamiania w Steam i
nie używa moda CAPIE jako przełącznika: dopóki jest zainstalowana, CAPIE ładuje się w każdej
uruchomionej grze.

1. Uruchom instalator jeszcze raz i wybierz **Uninstall**, żeby obie metody na siebie nie
   nachodziły.
2. Pobierz pliki wydania jak w sposobie B i uruchom w tym folderze:

    ```powershell
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -Install -PackagePath .\CAPIE-1.5.0-win64.zip -LoadMethod Proxy -ProxyActivation Config
    ```

3. Uruchamiaj grę w dowolny sposób. Jej log to `%LOCALAPPDATA%\RenameAnything\proxy.log`.

Jeśli instalator nie może zapisać do folderu gry, uruchom PowerShell jako administrator na czas
tego kroku. Instalator nigdy nie podmienia `version.dll`, którego sam nie zainstalował; jeśli inny
mod albo program już go tam ma, tej metody nie da się użyć.

Żeby ją wyłączyć, usuń `%LOCALAPPDATA%\RenameAnything\proxy.enabled` albo odinstaluj CAPIE.

### Dalej nie działa

Załóż zgłoszenie na [GitHubie](https://github.com/capie-mods/rename-anything/issues) albo napisz
komentarz na stronie w Workshopie i podaj:

- wersję gry z menu głównego,
- zawartość opcji uruchamiania w Steam,
- `launcher.log` (oraz `bootstrap.log` z tego samego folderu, jeśli nie udała się instalacja).

Logi zawierają ścieżki i numery procesów, nigdy wpisanych nazw.

## Gra wieloosobowa

CAPIE nie było testowane w grze wieloosobowej. Przed grą wieloosobową wyłącz mod CAPIE w zestawie
modów albo uruchom instalator i wybierz **Disable** (usuwa CAPIE z opcji uruchamiania w Steam;
pliki zostają).

## Aktualizacje

CAPIE nigdy nie aktualizuje się samo. Uruchom ponownie polecenie z jedną linią i wybierz
**1 Install or update**. Poprzednia wersja zostaje na dysku; pobrany skrypt uruchomiony z
`-Rollback` (jak w sposobie B) przełącza z powrotem na nią.

## Odinstalowanie

1. Uruchom polecenie z jedną linią i wybierz **Uninstall**. Usuwa CAPIE i przywraca opcje
   uruchamiania w Steam do stanu sprzed instalacji. W folderze gry nic nie trzeba naprawiać (przy
   metodzie proxy usuwa tylko swój `version.dll`).
2. Anuluj subskrypcję Rename Anything i CAPIE w Workshopie.

Ustawione nazwy zostają w zapisach, które zrobiłeś. Żeby pozbyć się własnej nazwy kraju, użyj w
grze **Przywróć nazwę**, zanim usuniesz mod. Kontynuowanie starego zapisu bez moda nie było
testowane; spróbuj na kopii.

## Bez CAPIE { #without-capie }

Na macOS, na Linuksie, na nieobsługiwanej wersji gry albo gdy po prostu nie chcesz części
natywnej, Rename Anything dalej działa dla stanów, miast (punktów zwycięstwa) oraz generałów,
admirałów i doradców (decyzja „Zmień nazwy postaci”, pisanie na klawiaturze ekranowej). Ołówki
przy kraju, przywódcy i partiach, zmiana nazw państw podległych i frakcji oraz flagi wymagają
CAPIE i bez niego są ukryte.
