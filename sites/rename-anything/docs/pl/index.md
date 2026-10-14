---
description: Rename Anything pozwala zmienić w Hearts of Iron IV nazwę państwa, jego przywódcy, partii, stanów i miast, w miejscu, w którym nazwa jest widoczna.
---

# Rename Anything

In English: [Rename Anything](../index.md).

<p class="endorse">Zbudowane na CAPIE</p>

<p class="lead">Kliknij ołówek obok nazwy, wpisz nową, naciśnij Enter. Rename Anything pozwala
zmienić w Hearts of Iron IV nazwę państwa, jego przywódcy, partii, stanów i miast, w panelu, w
którym nazwa jest widoczna. Jako zwierzchnik możesz też zmieniać nazwy swoich podmiotów.</p>

!!! warning "Wersja przedpremierowa"

    Rename Anything nie ma jeszcze w Steam Workshop. Funkcje oznaczone
    <span class="st st-today">Działa dziś</span> sprawdzono w grze na wersjach rozwojowych,
    w grze jednoosobowej, HOI4 1.19.3.0. Gra wieloosobowa nie jest obsługiwana.

HOI4 pozwala nazwać dywizję, jak chcesz, ale własne państwo, jego przywódca i partia rządząca
mają nazwy, które nadała gra albo drzewko narodowe. Rename Anything daje zamiast tego prawdziwe
pole tekstowe: każda nazwa, którą da się wpisać, także z polskimi literami, zapisana w kampanii.

<figure class="diagram" markdown="span">
  ![Hearts of Iron IV diplomacy screen with a subject renamed to Province of Rizzia, its leader Rizzler King and its Rizz Party; the map shows the new name across Canada.](../assets/screenshots/hero.jpg)
  <figcaption>Kanada przemianowana przez zwierzchnika na Province of Rizzia: nowa nazwa na mapie i w dyplomacji.</figcaption>
</figure>

<figure class="diagram" markdown="span">
  ![Zmiana nazwy przywódcy: kliknij ołówek, wpisz Jan Żółć w polu tekstowym gry, naciśnij Enter. Nazwa trafia do zapisu gry.](../assets/diagrams/edit-in-place.svg)
  <figcaption>Zmieniasz nazwę tam, gdzie ją widzisz. Nowa nazwa trafia do zapisu gry jak każda inna zmiana.</figcaption>
</figure>

## Co możesz przemianować

<ul class="st-legend">
  <li><span class="st st-today">Działa dziś</span> sprawdzone w grze</li>
  <li><span class="st st-progress">W przygotowaniu</span> zbudowane, jeszcze niesprawdzone albo nieskończone</li>
  <li><span class="st st-planned">Planowane</span> postanowione, jeszcze niezbudowane</li>
  <li><span class="st st-not">Nieobsługiwane</span> nie polegaj na tym</li>
</ul>

| Obiekt | Gdzie | Stan |
|---|---|---|
| Nazwa i przymiotnik państwa | Ołówek przy tytule panelu Polityka | <span class="st st-today">Działa dziś</span> wymaga CAPIE; flaga i kolor bez zmian |
| Przywódca państwa | Ołówek obok portretu w panelu Polityka | <span class="st st-today">Działa dziś</span> |
| Partia rządząca, krótka i pełna nazwa | Ołówek w panelu Polityka | <span class="st st-today">Działa dziś</span> |
| Partie pozostałych grup ideologicznych | Ten sam edytor, jedna zakładka na grupę | <span class="st st-progress">W przygotowaniu</span> sprawdzone 2 z 4 grup |
| Stany | Widok stanu na mapie albo edytor nazw | <span class="st st-today">Działa dziś</span> |
| Miasta (punkty zwycięstwa) | „Miasta” w widoku stanu albo edytor nazw | <span class="st st-today">Działa dziś</span> |
| Generałowie, admirałowie, doradcy | Edytor nazw, z decyzji „Zmień nazwy postaci” | <span class="st st-today">Działa dziś</span> |
| Podmioty: nazwa i przymiotnik, przywódca, partia rządząca | Dyplomacja, akcja „Zmień nazwy tego państwa” | <span class="st st-today">Działa dziś</span> wymaga CAPIE |
| Powrót do nazwy państwa z gry | „Przywróć nazwę” w edytorze państwa | <span class="st st-progress">W przygotowaniu</span> |
| Nazwa frakcji | Dyplomacja, akcja „Zmień nazwę frakcji” | <span class="st st-progress">W przygotowaniu</span> wymaga CAPIE 1.4; sprawdzone raz na wersji rozwojowej |
| Flaga państwa | Karta „Flaga” w edytorze państwa i podmiotu | <span class="st st-progress">W przygotowaniu</span> wymaga CAPIE 1.4; sprawdzone raz na wersji rozwojowej |

Nazwy przetrwają zapis, wczytanie i pełne ponowne uruchomienie gry. Etykiety na mapie,
dyplomacja, podpowiedzi i wydarzenia używają nowej nazwy państwa; tytuły decyzji zachowują swój
tekst.

Host może też ustawić w lobby 2 [reguły gry](reguly-gry.md): kto może zmieniać nazwy i czy
zmiana nazwy państwa trafia do wiadomości.

## Co wymaga CAPIE

Rename Anything to zwykłe pliki skryptów i interfejsu HOI4. Niektóre rzeczy wymagają więcej, niż
potrafi skrypt, i te zapewnia CAPIE (Cyprian's API Extender), mała biblioteka natywna:

- nazwy i przymiotniki państwa i podmiotów, bo gra nie ma efektu skryptowego, który przyjmuje
  dowolny tekst dla państwa;
- pola tekstowe w panelach, bo skrypt nie odczyta tego, co wpisujesz w pole tekstowe gry;
- natychmiastowa zmiana nazwy przywódcy w otwartym panelu Polityka.

Stany, miasta i postacie działają bez CAPIE, przez edytor nazw i jego klawiaturę ekranową. Bez
CAPIE ołówki, które go wymagają, są ukryte, a państwo ma nazwę z gry.

[Jak używać](jak-uzywac.md){ .md-button .md-button--primary } [Instalacja](instalacja.md){ .md-button }
