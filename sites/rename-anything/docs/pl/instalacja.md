---
description: Instalacja Rename Anything. Planowane wydanie ze Steam Workshop, instalatorem CAPIE i przełącznikiem CAPIE w zestawie modów oraz dzisiejsza konfiguracja rozwojowa.
---

# Instalacja

## W pierwszym wydaniu <span class="st st-progress">W przygotowaniu</span> { #first-release }

Nic nie jest jeszcze opublikowane. Tak to będzie działać:

1. Zasubskrybuj w Steam Workshop **Rename Anything** i mały mod **CAPIE** i dodaj oba do zestawu
   modów (playset) w Paradox Launcherze, jak każdy inny mod.
2. Zainstaluj CAPIE raz. Są 2 sposoby, wynik jest ten sam:
    - jedna linia w PowerShell (`irm ... | iex`). Uruchamia instalator w terminalu, z krótką
      animacją, i pyta, zanim cokolwiek zmieni;
    - instalator ze strony GitHub Releases projektu.
3. Naciśnij Graj w Steam, wybierz zestaw modów i graj. CAPIE ładuje się tylko wtedy, gdy mod
   CAPIE jest włączony w zestawie, z którym uruchamiasz grę.

<figure class="diagram" markdown="span">
  ![Kolejność uruchamiania: Graj w Steam albo skrót uruchamia launcher CAPIE, potem Paradox Launcher, potem grę z CAPIE. Przy nieznanej wersji gry gra uruchamia się bez CAPIE.](../assets/shared/diagrams/launch-chain.svg)
  <figcaption>Launcher CAPIE przechodzi przez Paradox Launcher, więc zestawy modów działają jak zwykle.</figcaption>
</figure>

### Włączanie i wyłączanie CAPIE

Mod CAPIE w zestawie modów jest przełącznikiem. Nie zawiera treści do gry.

- Włączony: launcher CAPIE ładuje CAPIE do gry.
- Wyłączony albo nieobecny w zestawie: gra uruchamia się bez CAPIE, jakby nie było
  zainstalowane.

Wyłącz go przed grą wieloosobową. Aby całkiem usunąć CAPIE, uruchom instalator ponownie i wybierz
odinstalowanie; przywraca on to, co zmienił.

Polecenie i wydanie zostaną opublikowane razem. Do tego czasu instalator celowo odmawia
działania. Dokumentacja CAPIE opisuje szczegółowo instalator, jego opcje, aktualizacje i
odinstalowanie.

Bez CAPIE mod nadal działa dla stanów, miast i postaci. Ołówki państwa, przywódcy i partii oraz
zmiana nazw podmiotów wymagają CAPIE i bez niego są ukryte.

## Dziś: wersje rozwojowe

Dla testerów, którzy dobrze się czują w konfiguracji deweloperskiej.

1. Zachowaj cały folder `mod/` z repozytorium, na przykład
   `C:/Users/you/Documents/GitHub/hoi4-rename-anything/mod`.
2. W folderze użytkownika HOI4 (`Documents/Paradox Interactive/Hearts of Iron IV/mod/`) utwórz
   `rename_anything_dev.mod`. `path` musi wskazywać folder `mod`, który zawiera `common/`,
   `interface/` i `descriptor.mod`:

    ```text title="rename_anything_dev.mod"
    name="Rename Anything (dev)"
    path="C:/Users/you/Documents/GitHub/hoi4-rename-anything/mod"
    version="0.1.0"
    supported_version="1.19.*"
    ```

3. Dodaj mod do zestawu modów w Paradox Launcherze. Nie musisz zmieniać `dlc_load.json` ani
   żadnego pliku gry.
4. Do funkcji, które wymagają CAPIE, zbuduj CAPIE i załaduj je do uruchomionej gry, jak opisuje
   `plugin/capie/README.md` w repozytorium. Powtarzaj to przy każdym uruchomieniu gry.

`supported_version="1.19.*"` tylko wycisza ostrzeżenie launchera. Testowano wyłącznie 1.19.3.0.

## Odinstalowanie { #odinstalowanie }

Wyłącz mod w zestawie modów i usuń `rename_anything_dev.mod` (oraz skopiowany folder, jeśli go
utworzyłeś). Zamknij grę, aby wyładować CAPIE. W folderze gry nie trzeba niczego naprawiać.

Nadane nazwy zostają w zapisach, które zrobiłeś. Aby usunąć z zapisu własną nazwę państwa,
przywróć nazwę w grze przed odinstalowaniem. Kontynuowania starego zapisu bez moda nie testowano;
spróbuj na kopii.
