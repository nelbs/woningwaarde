# Woningwaarde

Home Assistant-integratie voor een **geindexeerde woningwaarde** op basis van de openbare CBS/Kadaster Prijsindex Bestaande Koopwoningen (2020=100). Geen API-sleutel, scraping of verzoeken aan BerekenHet nodig.

## Installeren en woningen toevoegen

1. Installeer als aangepaste HACS-repository (`nelbs/woningwaarde`, categorie Integratie), zodra deze versie daar gepubliceerd is. Voor deze lokale versie: kopieer `custom_components/woningwaarde` naar de map `config/custom_components/woningwaarde` van Home Assistant.
2. Herstart Home Assistant.
3. Ga naar **Instellingen > Apparaten & diensten > Integratie toevoegen > Woningwaarde**.
4. Vul een blijvend woning-ID in (bijvoorbeeld `thuis`), een naam, CBS-reeks, bekende waarde in euro en de bijbehorende datum.
5. Voeg voor iedere volgende woning opnieuw Woningwaarde toe, met een ander woning-ID. Gelijke namen/prijzen zijn toegestaan.
6. Gebruik **Opnieuw configureren** in het integratiemenu om naam, reeks, prijs of datum aan te passen. Het woning-ID blijft gelijk, evenals de sensoridentiteit.

De sensor is numeriek, met valuta EUR. Iedere woning heeft een eigen apparaat en sensor met unieke ID. Attributen tonen de gekozen reeks, CBS-tabel, referentiewaarde en -datum, beide indices en beide kwartalen. Bij een bronfout wordt de sensor niet beschikbaar; een oude waarde wordt niet als actuele waarde aangeboden.

## Berekening en dekking

`waarde = bekende waarde * laatst gepubliceerde kwartaalindex / index van het referentiekwartaal`

De datum wordt ingedeeld in het kalenderkwartaal waarin hij ligt. Er is geen daginterpolatie of extrapolatie. Het laatst gepubliceerde kwartaal staat in `latest_period`: dagelijkse controle betekent niet dat CBS dagelijks nieuwe cijfers publiceert. Een datum vanaf 1995 is toegestaan, maar het referentiekwartaal moet al gepubliceerd zijn; anders blijft de configuratie bestaan en meldt de integratie bij het laden de ontbrekende index. Kies in dat geval via opnieuw configureren een gepubliceerde referentiedatum.

Beschikbare keuzes:

- Nederland, alle twaalf provincies en de vier grote gemeenten Amsterdam, Den Haag, Rotterdam en Utrecht: **alle woningtypen samen** (85792NED).
- Landelijk per woningtype: eengezinswoning, tussenwoning, hoekwoning, twee onder een kap, vrijstaand of appartement (85791NED).

CBS biedt in deze tabellen geen kruising provincie x woningtype. De integratie combineert de twee indices daarom niet tot een verzonnen regionale woningtype-index. Voor andere gemeenten kies je de provincie. De uitkomst volgt een gemiddelde prijsontwikkeling; het is geen individuele taxatie of actuele WOZ-waarde.

## Frequentie en netwerkbelasting

Iedere woningcoordinator controleert eens per 24 uur. Alle woningen delen dezelfde **op schijf opgeslagen** cache van de twee CBS-tabellen. Per gebruikte tabel wordt hoogstens eens per 24 uur een nieuwe ophaalpoging gedaan, ook bij herladen, herstarten, handmatig bijwerken of een bronfout. Woningen die dezelfde tabel gebruiken veroorzaken geen extra CBS-verzoeken. Per tabel is normaal een GET nodig; bij CBS-paginering worden vervolgpagina's binnen dezelfde poging opgehaald. Alleen gebruikte tabellen worden opgehaald. Het verwijderen van de cache of een tweede HA-installatie valt buiten deze limiet.

HTTP-time-out: 30 seconden per verzoek, 60 seconden voor de hele ophaalpoging. Geen automatische netwerkretry binnen de 24 uur; na een mislukte poging kan herstel dus maximaal circa een dag duren. De API ontvangt geen woningnamen, adressen of prijzen. De configuratie en cache worden lokaal door Home Assistant opgeslagen.

## Overstappen van versie 0.x (YAML)

Deze versie vervangt de oude YAML-sensor; automatische conversie is niet inbegrepen.

1. Bewaar je bestaande naam, `waarde`, `datum`, `region` en `type`.
2. Verwijder de oude `- platform: woningwaarde` uit de `sensor:`-configuratie.
3. Installeer de nieuwe bestanden, herstart en voeg iedere woning via de interface toe.
4. Zet de oude datum `dd-mm-jjjj` om naar de datumkiezer. Kies expliciet een regionale reeks **of** landelijke woningtypereeks. Een oude combinatie van regio en type wordt niet stilzwijgend overgenomen.
5. Pas dashboards/automatiseringen aan de nieuwe entity-ID aan. Historie wordt niet automatisch gekoppeld; bewaar de oude registratie totdat je de overstap hebt gecontroleerd.

De oude implementatie verstuurde formulier-POSTs met een vast sessiekenmerk naar BerekenHet, had een interval van 300 seconden en startte bovendien vanuit de constructor een verzoek. De nieuwe implementatie gebruikt uitsluitend asynchrone CBS-GETs.

## API-onderzoek

Gecontroleerd op 18 oktober 2026:

- [BerekenHet](https://www.berekenhet.nl/wonen-en-hypotheek/woning-waarde-huizenprijzen.html) beschrijft zelf dat de calculator de CBS/Kadaster PBK 2020 gebruikt. De site extrapoleert bovendien de laatste trend. Er is bij dit onderzoek geen openbare, gedocumenteerde BerekenHet-API aangetroffen; dit bewijst niet dat er geen private API bestaat.
- [CBS regionale prijsindex 85792NED](https://www.cbs.nl/nl-nl/cijfers/detail/85792NED) biedt regio's en kwartaalcijfers vanaf 1995. [Openbare API](https://opendata.cbs.nl/ODataApi/OData/85792NED).
- [CBS woningtype-index 85791NED](https://www.cbs.nl/nl-nl/cijfers/detail/85791NED) biedt landelijke kwartaalreeksen per woningtype. [Openbare API](https://opendata.cbs.nl/ODataApi/OData/85791NED).

Beide echte API-queries zijn succesvol uitgevoerd: 2646 regionale kwartaalrijen en 1008 woningtype-kwartaalrijen, zonder vervolgpagina. De respons liep tijdens de controle tot 2026KW02. Kleine responsfragmenten staan als testfixtures in `tests/fixtures/cbs.json` (bron: CBS/Kadaster).

## Ontwikkeling en validatie

Doel: Home Assistant 2026.10 of nieuwer. Unit tests: `python -m unittest discover -s tests -v` (vereist aiohttp en voluptuous). De tests isoleren de HA-grens met stubs; ze testen geen echte draaiende HA-installatie. Ze controleren de prijsverhouding, datum/prijsvalidatie, ontbrekende indices, echte CBS-fragmenten, gedeelde cache, gelijktijdige verzoeken, herstart, 24-uursgrens, foutbegrenzing en paginering.

Controleer voor ingebruikname in een testinstallatie: twee woningen toevoegen, herconfigureren, herstarten, sensorwaarde/attributen en onbeschikbaarheid bij een bronfout. De prerelease is bedoeld voor testen via HACS; er is geen volledige live Home Assistant-validatie uitgevoerd.

## Automatische WOZ-waarde

Onderzocht op 18 oktober 2026. Alleen automatisch ophalen via een blijvend gratis bron is gewenst. Er is geen gedocumenteerde, voor particuliere Home Assistant-gebruikers toegankelijke en blijvend gratis WOZ-API gevonden. Daarom bevat deze versie geen automatische WOZ-sensor en geen betaalde of handmatige WOZ-invoer.

- De [officiele WOZ API Bevragen](https://www.kadaster.nl/zakelijk/producten/adressen-en-gebouwen/woz-api-bevragen) is alleen voor gemeenten en vereist OIN en PKIO-certificaat.
- Volgens de [Waarderingskamer](https://www.waarderingskamer.nl/woz-wijzer/controleren-woz-waarde/woz-waardeloket) is geautomatiseerd uitlezen van het gratis WOZ-waardeloket niet toegestaan. Dat loket wordt niet gescrapet.
- [Altum](https://docs.altum.ai/woningdata/woz-api) biedt een externe API met eigen sleutel. Een gratis account is geen bewijs van blijvend gratis WOZ-opvragingen.
- [Wozapi](https://woz-api.nl/docs) biedt proefcredits; nieuwe succesvolle adresopvragingen kosten credits, met een tijdelijke vrijstelling voor herhaalde opvragingen. Dat voldoet niet aan de eis blijvend gratis.

De bestaande referentiewaarde voor de CBS-berekening mag een al bekende WOZ-waarde zijn. Dat maakt de uitkomst nog geen officiele of automatisch opgehaalde WOZ-waarde.

## Update 1.0.1: woningnaam en icoon

De sensor en het apparaat gebruiken nu rechtstreeks het veld **Naam** uit de integratieconfiguratie, bijvoorbeeld `haviklaan 28`. Het standaard sensoricoon is `mdi:home-outline`; de eerdere icoonnaam was niet geschikt.

Vervang de componentmap door die uit versie 1.0.1 en herstart Home Assistant. Controleer via **Opnieuw configureren** dat het veld Naam de gewenste woningnaam bevat. Het woning-ID is een apart identificatieveld en bepaalt de getoonde naam niet.

Bestaande entity-ID's blijven behouden voor dashboards en automatiseringen. Zelf ingestelde namen of iconen in de entiteitsinstellingen hebben voorrang; wis zo'n overschrijving om de standaard van de integratie te gebruiken. Het icoonveld mag leeg zijn: dat betekent dat Home Assistant het standaardicoon van de integratie gebruikt.

## Prerelease v1.0.1b1 via HACS

Deze testversie staat op de branch `feature/ui-multiple-homes` en wordt aangeboden als GitHub-prerelease `v1.0.1b1`. Minimumversie: Home Assistant 2026.10.0.

Open Woningwaarde in HACS en kies via het menu **Opnieuw downloaden / Redownload** de versie `v1.0.1b1`. Schakel zo nodig de HACS-optie voor prereleases/betaversies in. Herstart Home Assistant na de update. De keuze voor prereleases wordt door HACS aangeboden; de precieze plaats verschilt per HACS-versie.

De oude YAML-configuratie werkt niet meer met deze herbouw: volg de overstapinstructies hierboven. Bewaar een backup voor je bijwerkt.

## Prerelease v1.0.1b2: integratie-icoon

Een eigen huisicoon met oplopende waardebalken staat nu in `custom_components/woningwaarde/brand/`, in 256 en 512 pixels en met een variant voor donkere thema's. Home Assistant gebruikt deze lokale afbeeldingen voor de integratie. Het sensoricoon blijft `mdi:home-outline`.

Werk via HACS bij naar `v1.0.1b2`, herstart Home Assistant en vernieuw de browserpagina als het oude icoon nog uit de cache wordt getoond.

## Prerelease v1.0.1b3: euroteken in het icoon

Het huisje en de kleuren blijven behouden. Een groot euroteken en een klein oplopend grafiekje maken de woningwaarde herkenbaar. Werk via HACS bij naar `v1.0.1b3`, herstart Home Assistant en vernieuw de browserpagina.
