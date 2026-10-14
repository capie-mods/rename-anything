---
description: 2 reguły gry Rename Anything, które host ustawia w lobby. Kto może zmieniać nazwy i wiadomość, gdy państwo zmienia nazwę.
---

# Reguły gry

<span class="st st-progress">W przygotowaniu</span> Obie reguły są w modzie i przechodzą
kontrole poza grą. Nie zostały jeszcze sprawdzone w grze.

Host ustawia je w lobby, w regułach gry, jak każdą inną regułę. Same reguły nie blokują
osiągnięć; mod i tak zmienia sumę kontrolną gry (zobacz [FAQ](faq.md#osiagniecia)).

## Kto może zmieniać nazwy

„Rename Anything: kto może zmieniać nazwy”

| Opcja | Znaczenie |
|---|---|
| Własne państwo i podmioty (domyślnie) | Gracze zmieniają nazwy swojego państwa i swoich podmiotów. Lider frakcji zmienia nazwę frakcji. |
| Host zmienia nazwy wszystkich państw | Jak wyżej, a host może zmieniać nazwy wszystkich państw i wszystkich frakcji. |
| Tylko własne państwo | Gracze zmieniają tylko nazwę swojego państwa, nie podmiotów. Lider frakcji nadal zmienia nazwę frakcji. |

Gra nie potrafi powiedzieć skryptowi, kto jest hostem. W grze jednoosobowej hostem jesteś ty. W
grze wieloosobowej opcja dla hosta nic nie robi, dopóki CAPIE nie będzie umiało zgłosić, kto jest
hostem.

Jeśli reguła nie pozwala na zmianę nazwy, edytor mówi „Ustawienia gry nie pozwalają zmienić tej
nazwy. Nic nie zmieniono.”

## Wiadomość o nowej nazwie państwa

„Rename Anything: wiadomość o nowej nazwie państwa”

| Opcja | Znaczenie |
|---|---|
| Wyłączone (domyślnie) | Nazwy państw zmieniają się po cichu. |
| Włączone | Każdy dostaje wydarzenie z wiadomością, gdy gracz zmieni nazwę państwa albo przywróci jego pierwotną nazwę. |

Tytuł wydarzenia brzmi „*stara nazwa* zmienia nazwę na *nowa nazwa*”. Gdy stara nazwa nie jest
znana, tytuł brzmi „*nowa nazwa* przyjmuje nową nazwę”. Tekst to jedna z 4 krótkich relacji,
które wspominają stolicę, przywódcę albo przymiotnik. Zamykasz je przyciskiem „Przyjęto do
wiadomości.”

Na razie stara nazwa jest znana tylko wtedy, gdy państwo miało już nazwę nadaną przez gracza.
Nowsze CAPIE poda też nazwę z gry w chwili zmiany.
