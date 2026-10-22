# Validatie - 18 oktober 2026

- 23 geisoleerde unit tests geslaagd: berekening, invoervalidatie, echte CBS-fragmenten, meerdere woningen, dubbele woning-ID, herconfiguratie, gedeelde cache, gelijktijdige verzoeken, herstart, 24-uursgrens, mislukte pogingen en paginering.
- Ruff lint en formatter gecontroleerd; Python-compilatie geslaagd.
- De twee echte CBS API-queries succesvol uitgevoerd, inclusief de veldnamen en spaties in regionale codes. Geen woninggegevens verstuurd.
- Home Assistant config-flow- en coordinatorpatronen getoetst aan de officiele ontwikkelaarsdocumentatie. Geen volledige Home Assistant-installatie gestart: de HA-grens wordt in de unit tests vervangen door stubs.
- Geen live UI-, laad/ontlaad-, apparaatregistratie- of installatieproef uitgevoerd. Die blijven nodig op een testinstallatie voordat deze versie als release wordt gebruikt.
- Prerelease v1.0.1b1 voorbereid voor GitHub/HACS op feature/ui-multiple-homes; geen bestaande HA-installatie gewijzigd.

## Praktijkcontrole in Home Assistant

1. Verwijder de oude YAML-platformconfiguratie en installeer de nieuwe componentmap.
2. Herstart; voeg een woning toe met een referentiedatum in een gepubliceerd kwartaal.
3. Voeg een tweede woning toe met een eigen ID; controleer twee apparaten/sensoren.
4. Herconfigureer de referentiewaarde; controleer dat dezelfde sensor bijgewerkt wordt.
5. Herstart en werk handmatig bij binnen 24 uur; controleer dat de opgeslagen CBS-cache gebruikt wordt.
6. Controleer bij een bronstoring dat de sensor niet beschikbaar wordt en er binnen de 24-uursgrens geen nieuwe netwerkpoging plaatsvindt.

## Testcommando's

```text
python -m unittest discover -s tests -v
python -m ruff check --no-cache .
python -m ruff format --check .
python -m compileall -q custom_components
```

Versie 1.0.1: drie extra regressietests voor de ingevoerde woningnaam (inclusief haviklaan 28), sensoridentiteit bij hernoemen en het standaard huisicoon. De HA-grens blijft gestubd; geen live installatieproef uitgevoerd.

## Versie v1.0.1b4

35 geisoleerde tests geslaagd. Extra dekking: multiplicatieve correctie, wegvallen van de correctie bij alle woningtypen of regio Nederland, het laatste gemeenschappelijke kwartaal, ontbrekende referentieindices, echte CBS-responsfragmenten voor alle drie reeksen, afgerond BerekenHet-voorbeeld, behoud van oude configuraties, coordinatorselectie van tabellen, sensorattributen en foutafhandeling. Bestaande cache-, naam- en icoontests blijven slagen. HA-grens is gestubd; geen live HA-installatietest.

## Versie v1.0.1b5 - 22 oktober 2026

51 geisoleerde tests geslaagd. Zie docs/analysis-2026-10-22.md voor de bronvergelijking en de resterende, niet weggefitte afwijking ten opzichte van BerekenHet. Nieuwe tests dekken de dagconventie, lineaire interpolatie/extrapolatie, 21/92 dagen in het gebruikersvoorbeeld, 93 historische grafiekpunten, datumgrenzen, ontbrekende kwartalen, schrikkeldagen en de expliciete methodekeuze. De bestaande dagelijkse cache en standaard voor bestaande configuraties blijven behouden. HA-grens is gestubd; geen live HA-installatietest.

## Versie v1.0.1b6 - 23 oktober 2026

54 geisoleerde tests geslaagd. Nieuwe regressie: een controle 0,5 seconde voor het verstrijken van 24 uur gebruikt de cache; de volgende uurlijkse controle haalt de inmiddels beschikbare Q3-cijfers op. Verder getest: 24 uurlijkse cachecontroles veroorzaken slechts een netwerkpoging; diagnostische tijdstempels onderscheiden lokale controle van een echte bronpoging en tonen de correcte 24-uursgrens. Het planningsgedrag is gecontroleerd in de broncode van Home Assistant 2026.10.2 (`int(loop.time())` plus een willekeurige fractie). Geen volledige live HA-timertest; de coordinatorgrens in de tests is gestubd.

## Versie v1.0.1b7 - 23 oktober 2026

58 geisoleerde tests geslaagd. Nieuwe tests controleren de waarderingsdatum rond Nederlandse middernacht, een westelijke tijdzone, de winteroffset en invoervalidatie op de lokale kalenderdag. HA's tijdzonehelper wordt aangeroepen; in de unit tests is die grens gestubd met expliciete tijdzonebewuste tijdstippen. De bestaande 54 tests blijven slagen. De gebruiker heeft met sensorattributen bevestigd dat Q3 inmiddels opgehaald is; er is geen eigen volledige live HA-test uitgevoerd.
