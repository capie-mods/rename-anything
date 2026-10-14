# LinkedIn post draft

Drafts only. Nothing is published. Replace `<link>` once the repository or Workshop page is
public, and check the status lines against the README on the day of posting.

Images, in `docs/assets/promo/rename-anything/linkedin/`:

- `linkedin-1200x627-subject.jpg`: the renamed subject on the map, for a link post.
- `linkedin-1200x627-editor.jpg`: the country editor close up, as an alternative.
- `linkedin-1080x1080.jpg`: square, for an image post.

For a carousel, the eight Workshop gallery images in
`docs/assets/promo/rename-anything/workshop/` (1920 x 1080, with captions) work as they are.

## English

In Hearts of Iron IV you can name a division anything you like, but not your own country. Its
name, its leader and its ruling party are whatever the game or a focus tree decides.

I have been building Rename Anything, a mod that fixes this. You click a pencil next to the name,
type into the game's own text field and press Enter. It covers your country (name, adjective and
flag), the leader, parties, subjects, factions, states and cities. The names go into the save
like any other change in the campaign.

The hard part was that HOI4's script language has no strings. A script cannot read what the
player typed, and there is no effect that gives a country a free-text name. So the mod sits on
CAPIE (Cyprian's API Extender), a small native library I wrote for it. CAPIE passes the typed
text to the mod inside the same game command a button click sends, and draws custom country,
faction and flag names as their own layer. It changes no game files, opens no network
connections, and only starts on the exact game build whose hash it knows. On any other build the
game simply runs without it.

Where it stands: pre-release. Everything shown was checked in single player on HOI4 1.19.3.0
with development builds. Multiplayer has not been tested, so I do not claim it works there. The
installer and the Workshop release are next.

Source and documentation: <link>

The joke names in the screenshots are mine.

## Polski

W Hearts of Iron IV dywizję możesz nazwać, jak chcesz, ale własnego państwa już nie. Jego nazwę,
przywódcę i partię rządzącą ustala gra albo drzewko narodowe.

Robię mod Rename Anything, który to zmienia. Klikasz ołówek obok nazwy, wpisujesz nową w zwykłym
polu tekstowym gry i naciskasz Enter. Działa dla państwa (nazwa, przymiotnik i flaga), przywódcy,
partii, podmiotów, frakcji, stanów i miast. Nazwy trafiają do zapisu gry jak każda inna zmiana w
kampanii.

Najtrudniejsze było to, że język skryptów HOI4 nie ma tekstów. Skrypt nie odczyta, co gracz
wpisał, i nie ma efektu, który nadałby państwu dowolną nazwę. Dlatego mod korzysta z CAPIE
(Cyprian's API Extender), małej natywnej biblioteki, którą do tego napisałem. CAPIE przekazuje
wpisany tekst do moda w tym samym poleceniu gry, które wysyła kliknięcie przycisku, i wyświetla
własne nazwy państw i frakcji oraz flagi jako osobną warstwę. Nie zmienia plików gry, nie łączy
się z siecią i uruchamia się tylko na tej wersji gry, której skrót zna. Na każdej innej gra po
prostu działa bez niego.

Na jakim etapie: przed wydaniem. Wszystko, co widać, sprawdziłem w grze jednoosobowej na HOI4
1.19.3.0, na wersjach rozwojowych. Gry wieloosobowej nie testowałem, więc nie twierdzę, że tam
działa. Następne kroki to instalator i wydanie w Steam Workshop.

Kod i dokumentacja: <link>

Żartobliwe nazwy na zrzutach są moje.
