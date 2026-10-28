---
description: Częste pytania o Rename Anything. Gra wieloosobowa, osiągnięcia, ostrzeżenia antywirusa, aktualizacje gry, flagi i odinstalowanie.
---

# FAQ

## Czy potrzebuję CAPIE? { #capie }

Do nazwy państwa, ołówków w panelu Polityka i zmiany nazw podmiotów tak. Do stanów, miast i
postaci nie: działają przez edytor nazw na samych skryptach.

## Czy zmiana nazwy państwa zmienia flagę? { #flaga }

Nie. Nadana nazwa jest przechowywana niezależnie od tagów kosmetycznych gry, więc flaga i kolor
zostają takie, jak ustawia gra. Wybór własnej flagi jest planowany jako osobna funkcja.

## Czy działa w grze wieloosobowej? { #gra-wieloosobowa }

Nie. Nigdy nie był testowany z 2 graczami, więc nie jest obsługiwany. Wyłącz CAPIE przed grą
wieloosobową: wyłącz mod CAPIE w zestawie modów.

## Czy nadal mogę zdobywać osiągnięcia? { #osiagniecia }

Nie. Każdy mod, który zmienia pliki w `common/`, zmienia sumę kontrolną gry, a osiągnięcia
wymagają niezmienionej sumy kontrolnej. Trybu Ironman nie testowano.

## Mój antywirus zgłasza ostrzeżenie. { #antywirus }

Chodzi o CAPIE, które ładuje się do gry. Niektóre złośliwe programy robią to samo, więc
ostrzeżenia heurystyczne są możliwe. Każdy wydany plik binarny zostanie przeskanowany w
VirusTotal, a wyniki będą podlinkowane w informacjach o wydaniu. Kod źródłowy jest publiczny i
możesz go zbudować samodzielnie.

## Co się dzieje po aktualizacji gry? { #aktualizacja-gry }

CAPIE jest przypięte do jednego, dokładnego pliku wykonywalnego HOI4 (1.19.4.0 od CAPIE 1.5.1). Po łatce gra uruchamia się
bez CAPIE i dostajesz informację dlaczego. Stany, miasta i postacie nadal działają. Własna nazwa
państwa jest pokazywana jako nazwa z gry, dopóki aktualizacja CAPIE nie obsłuży nowej wersji.

## Jakich liter mogę używać? { #litery }

Liter, cyfr, spacji, `-`, `.`, `'` i polskich liter, do 32 znaków. Wpisywanie polskich liter
bezpośrednio w pole tekstowe gry sprawdzono na 1 układzie klawiatury. Więcej alfabetów może dojść
później, jeśli czcionki gry je obsłużą.

## Dlaczego nie mogę od razu zmienić nazwy ponownie? { #limit-zmian }

Każda zmiana nazwy rozpoczyna 5-dniowy limit, liczony w dniach gry. Podpowiedź ołówka mówi, kiedy
możliwa jest kolejna zmiana. Przywrócenie nazwy liczy się jako zmiana nazwy.

## Czy inni gracze mogą zmienić nazwę mojego państwa? { #inni-gracze }

Domyślnie nie. Host wybiera w lobby, kto może zmieniać jakie nazwy; zobacz
[Reguły gry](reguly-gry.md). Zwierzchnik zawsze może zmieniać nazwy swoich podmiotów, chyba że
host wybierze „Tylko własne państwo”.

## Jak odinstalować? { #odinstalowanie }

Wyłącz mod w zestawie modów i usuń jego pliki. Zamknij grę, aby wyładować CAPIE. Nadane nazwy
zostają w zapisach, które zrobiłeś. Zobacz [Instalacja](instalacja.md#odinstalowanie).

## Czy działa z innymi modami? { #inne-mody }

Powinien działać z modami, które nie ruszają panelu Polityka i widoku stanu. Zobacz
[Znane problemy](znane-problemy.md#inne-mody).
