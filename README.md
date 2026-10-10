# Rename Anything (HOI4)

Mod do Hearts of Iron IV (cel: 1.19.x, obserwowana instalacja: 1.19.3.0 "Operation Postern"),
który pozwala graczowi swobodnie zmieniać z klawiatury nazwy:

- państw (nazwa, przymiotnik),
- regionów (stanów),
- miast / prowincji (victory points),
- liderów (postaci),
- partii politycznych (długa i krótka nazwa).

**Wymaganie twarde: musi działać identycznie w singleplayerze i w multiplayerze** (bez desynców,
bez checksum-mismatch problemów poza standardowym "wszyscy mają ten sam mod").

## Status

Szkielet repo. Implementacja jeszcze nie istnieje — patrz [docs/design.md](docs/design.md)
(założenia architektury, ryzyka do zweryfikowania prototypem).

## Struktura

```
descriptor.mod            # deskryptor moda
common/scripted_guis/     # logika okna rename (MP-safe: efekty przez kliknięcia GUI)
interface/                # .gui / .gfx okna i klawiatury
localisation/{english,polish}/
docs/                     # projekt i notatki techniczne
```

## Lokalny development

Utwórz w `Documents/Paradox Interactive/Hearts of Iron IV/mod/` plik `rename_anything.mod`:

```
name="Rename Anything (dev)"
path="C:/Users/user/Documents/GitHub/hoi4-rename-anything"
supported_version="1.19.*"
```

Testy MP: dwa klienty (np. drugi przez `-multiplayer` na LAN/hotjoin), ten sam zestaw modów,
po każdej zmianie nazwy sprawdzić brak OOS (`oos` w `game.log`, `error.log`).
