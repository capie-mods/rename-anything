---
description: Znane problemy w obecnych wersjach rozwojowych Rename Anything i co z nimi zrobić.
---

# Znane problemy

Pochodzą z ostatnich testów na wersjach rozwojowych (HOI4 1.19.3.0, gra jednoosobowa). Przy
każdym jest opis, co się dzieje i co robić, dopóki nie zostanie naprawiony.

## Tryb edycji zostaje po zamknięciu panelu Polityka <span class="st st-progress">W przygotowaniu</span> { #edit-mode }

Jeśli zamkniesz panel Polityka (na przykład klawiszem <kbd>Esc</kbd>), gdy edytor jest otwarty,
edytor znika razem z panelem, ale Rename Anything nadal uważa, że edytujesz.

Co zrobić: otwórz panel ponownie i zatwierdź albo anuluj edycję. Albo zatwierdź lub anuluj przed
zamknięciem panelu.

## Pole tekstowe przyjmuje więcej niż 32 znaki

Pole tekstowe gry pozwala pisać dalej po 32 znakach. Rename Anything odrzuca wtedy nazwę z
czerwoną linią („Nazwa nieprzyjęta: do 32 znaków, które gra wyświetli.”) i niczego nie zmienia.
Skróć nazwę i naciśnij <kbd>Enter</kbd> ponownie.

## Długa nazwa przywódcy wchodzi pod ołówek

W panelu Polityka długa nazwa przywódcy może sięgać ołówka obok portretu. Ołówek nadal działa.

## Gra wieloosobowa nie jest obsługiwana <span class="st st-not">Nieobsługiwane</span> { #multiplayer }

Rename Anything i CAPIE nigdy nie były testowane z 2 graczami. Nie używaj ich w grze
wieloosobowej. Wyłącz CAPIE, zanim dołączysz do gry wieloosobowej albo ją założysz.

## Nowe funkcje jeszcze niesprawdzone w grze <span class="st st-progress">W przygotowaniu</span> { #unchecked }

„Przywróć nazwę”, reguła „kto może zmieniać nazwy” i wyłączniki funkcji z
[reguł gry](reguly-gry.md) są w modzie, ale nie zostały jeszcze sprawdzone w grze. Nazwy frakcji
i flagi wymagają CAPIE 1.4, które istnieje tylko jako wersja rozwojowa; ze starszym CAPIE edytor
frakcji niczego nie zmienia i o tym informuje.

## Starsze zapisy z własną nazwą państwa

Zapisy z pierwszych wersji rozwojowych przechowywały własną nazwę państwa jako tag kosmetyczny,
co zmieniało też flagę. Takie państwo nadal pokazuje swoją nazwę. Przy pierwszej zmianie albo
przywróceniu nazwy Rename Anything przenosi ją do nowego miejsca przechowywania i usuwa ten tag
kosmetyczny. Tag kosmetyczny, który państwo miało wcześniej, nigdy nie był zapisany, więc nie
może wrócić.

## Inne mody { #inne-mody }

Rename Anything powinien działać z modami, które nie ruszają panelu Polityka i widoku stanu.
Mody, które zastępują `countrypoliticsview.gui` albo te same skryptowe GUI, mogą powodować
konflikty. Mody, które zmieniają mapę, identyfikatory stanów lub prowincji albo dodają punkty
zwycięstwa, wymagają ponownego wygenerowania tabel miast.
