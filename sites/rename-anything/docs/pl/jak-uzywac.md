---
description: Jak zmieniać nazwy w Rename Anything. Ołówki, Enter, zakładki partii, podmioty, frakcje, Przywróć nazwę, limit 5 dni, stany, miasta i postacie.
---

# Jak używać

Nazwę państwa, przywódcy i partii zmieniasz w panelu Polityka, a nazwy podmiotów i frakcji przez
dyplomację. Stany, miasta i postacie mają własny edytor. Każda sekcja mówi, czy wymaga CAPIE.

## Przywódca

1. Otwórz panel Polityka.
2. Kliknij mały ołówek obok portretu przywódcy. Jego podpowiedź to „Zmień nazwę przywódcy”.
3. W tym samym miejscu otwiera się pole tekstowe gry z obecną nazwą.
4. Wpisz nową nazwę i naciśnij <kbd>Enter</kbd> albo kliknij ikonę zatwierdzenia.

Nazwa pod portretem zmienia się od razu. Wymaga CAPIE, bo skrypt nie odczyta tego, co wpisujesz
w pole tekstowe gry.

## Partie

1. W panelu Polityka kliknij ołówek partii („Zmień nazwy partii”).
2. Edytor ma jedną zakładkę na grupę partii, jak zakładki w grze. Podpowiedź zakładki pokazuje
   obecną nazwę tej partii. Wybierz grupę; nie musi to być partia u władzy.
3. Wypełnij oba pola, „Krótka nazwa” i „Pełna nazwa”, i naciśnij <kbd>Enter</kbd>.

Nową nazwę partii widać w panelu od razu. Wymaga CAPIE. Wszystkie 4 grupy sprawdzono w grze.

## Nazwa i przymiotnik państwa

1. Kliknij ołówek w linii tytułu panelu Polityka („Zmień nazwę państwa”).
2. Wypełnij „Nazwa” i „Przymiotnik”. Oba pola są wymagane.
3. Naciśnij <kbd>Enter</kbd>.

Mapa, dyplomacja, podpowiedzi i wydarzenia używają nowej nazwy. Tytuły decyzji zachowują tekst,
z którym je napisano. Flaga i kolor zostają bez zmian: nadana nazwa jest przechowywana osobno,
niezależnie od tagów kosmetycznych gry. Jeśli gra później nada państwu nowy tag kosmetyczny (na
przykład przez narodowy cel), twoja nazwa nadal jest widoczna.

<span class="st st-progress">W przygotowaniu</span> Aby wrócić, kliknij „Przywróć nazwę” w tym
samym edytorze. Państwo dostaje nazwę, którą gra nadałaby mu teraz. Przywrócenie liczy się jako
zmiana nazwy w limicie zmian.

Wymaga CAPIE w każdej sesji gry. Bez CAPIE państwo ma nazwę z gry, a twoja nazwa wraca, gdy znów
uruchomisz grę z CAPIE.

## Podmioty

Jako zwierzchnik możesz zmieniać nazwy swoich podmiotów.

1. Zaznacz podmiot na mapie i otwórz jego zakładkę Dyplomacja.
2. Wybierz akcję „Zmień nazwy tego państwa”. Nic nie kosztuje i nie wymaga odpowiedzi.
3. Edytor ma 3 zakładki: „Państwo” (nazwa i przymiotnik), „Przywódca” i „Partia” (krótka i
   pełna nazwa partii rządzącej).
4. Wypełnij pola i naciśnij <kbd>Enter</kbd>.

Akcja pojawia się tylko przy twoich podmiotach, chyba że host wybrał inną
[regułę gry](reguly-gry.md). Wymaga CAPIE.

## Frakcja <span class="st st-progress">W przygotowaniu</span> { #frakcja }

Lider frakcji będzie mógł zmienić jej nazwę: akcja „Zmień nazwę frakcji” pojawia się w
Dyplomacji przy pozostałych członkach twojej frakcji. Z obecnym CAPIE edytor się otwiera, ale
informuje, że nazwy frakcji wymagają nowszego CAPIE, i nic się nie zmienia.

## Stany i miasta

Możesz zmieniać nazwy swoich stanów i miast (punktów zwycięstwa) w nich. CAPIE nie jest
potrzebne.

- Zaznacz swój stan na mapie. Obok panelu stanu z gry pojawia się mały panel „Zmiana nazw” z
  przyciskami „Zmień nazwę”, „Miasta” i „Przywróć”.
- „Miasta” pokazuje listę punktów zwycięstwa w tym stanie; wybierz jeden i zmień jego nazwę.
  Przy mieście, którego nazwę zmieniłeś, lista pokazuje „Pierwotna nazwa (obecnie Nowa nazwa)”.
- Te same listy są w edytorze nazw, na zakładkach „Stany” i „Miasta”.

## Generałowie, admirałowie i doradcy

Otwórz decyzje, znajdź kategorię „Rename Anything” i wybierz decyzję „Zmień nazwy postaci”.
Otwiera ona edytor nazw na zakładce „Postacie”, gdzie wybierasz postać z listy i wpisujesz nową
nazwę. Stany i miasta są w tym samym edytorze. CAPIE nie jest potrzebne.

Gdy CAPIE jest załadowane, edytor nazw używa pola tekstowego gry. Bez CAPIE ma klawiaturę
ekranową: litery, <kbd>Shift</kbd> + litera dla wielkich liter, cyfry, `-` i `.`;
<kbd>Backspace</kbd> kasuje, <kbd>Enter</kbd> zatwierdza. Polskie litery i `'` są na
przyciskach. Skróty klawiszowe gry działają, gdy tam piszesz.

## Ograniczenia i kontrole

- Najwyżej 32 znaki na nazwę. Dłuższy tekst jest odrzucany z czerwoną linią pod polem i nic się
  nie zmienia. Nic nie jest obcinane.
- Litery, cyfry, spacja, `-`, `.`, `'` i polskie litery ą ć ę ł ń ó ś ź ż (także wielkie).
  Inne litery, na przykład é, są odrzucane z komunikatem.
- Puste pole jest odrzucane.
- Każdy obiekt ma limit: 1 zmiana nazwy na 5 dni. W tym czasie ołówek jest wyszarzony, a jego
  podpowiedź ma dodatkową czerwoną linię, na przykład „Kolejna zmiana nazwy możliwa za 3 dni
  (ostatnia zmiana: 4 stycznia 1936).” Przy stanach i miastach edytor mówi „Nazwę stanu można
  zmieniać raz na 5 dni.” (albo „Nazwę miasta można zmieniać raz na 5 dni.”).
- Kto może zmieniać jakie nazwy, zależy od [reguł gry](reguly-gry.md). Domyślnie zmieniasz
  nazwy własnego państwa i swoich podmiotów.

## Gdzie są przechowywane nazwy

Każda nazwa jest zapisana w zapisie gry, jak każda inna zmiana w kampanii. Przetrwa zapis,
wczytanie i ponowne uruchomienie gry.
