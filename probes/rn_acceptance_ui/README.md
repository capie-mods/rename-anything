# Acceptance UI — osobny fixture QA

Nie jest częścią `mod/` ani wydania. **Włączony do następnej sesji QA 2026-10-11;
test w grze nadal oczekuje.** Aktywację i późniejsze sprzątanie śledzi
`docs/evidence/session-20261011/day2-acceptance-fixture-activation.json`.
Jeden widoczny przycisk w prawym górnym obszarze ekranu wywołuje na kraju gracza
oryginalny `news_event = { id = news.350 }`. Nie ma skrótu klawiaturowego,
własnych eventów, zmian nazw ani efektów kampanii poza wywołaniem wiadomości.

Vanilla HOI4 1.19.3.0: `events/NewsEvents.txt:13551` definiuje `news.350` jako
`is_triggered_only = yes`, `major = yes`. Brak bloku `immediate`; trzy opcje
zawierają wyłącznie nazwę i trigger, bez efektów. Właściwy efekt wywołania i scope
COUNTRY opisuje `documentation/effects_documentation.md:5053`.

Tytuł `news.350.t` odczytuje **`ROOT.GetNameDef`**, a opis `news.350.desc`:
`ROOT.GetAdjective`, `ROOT.GetLeader`, `ROOT.GetRulingIdeology` i
`ROOT.Capital.GetCapitalVictoryPointName`. Zwykły `GetName` nie jest tu wywoływany.
Własną nazwę miasta sprawdzisz przez ten event tylko po zmianie **stołecznego VP**;
Gdańsk nie jest stolicą startowej Polski. Definicje lokalizacji:
`localisation/english/events_l_english.yml:1946` i
`localisation/polish/events_l_polish.yml:1945`.

Aktywację wykonuje koordynator QA osobno, przy zamkniętej grze, dodając lokalny
descriptor wskazujący ten katalog oraz fixture do testowego playsetu obok moda.
Nie nadpisuj konfiguracji ani zapisów użytkownika. Po aktywacji uruchom kampanię,
ustaw nazwy testowanym modem, kliknij przycisk fixture i oceń wiadomość.
Widoczność wiadomości zależy też od ustawień news popup gry; brak popupu sam
w sobie nie dowodzi błędnej nazwy. Po teście wyłącz fixture w playsecie.

Przygotowanie fixture nie zmienia plików instalacji, aktywnego `mod/`, userdir,
procesów gry ani ustawień. Statyczna kontrola nie zastępuje testu na żywo.
