# Woningwaarde

Home Assistant-integratie voor een **geindexeerde woningwaarde** op basis van de openbare CBS/Kadaster Prijsindex Bestaande Koopwoningen (2020=100). Geen API-sleutel, scraping of verzoeken aan BerekenHet nodig.

## Installeren en woningen toevoegen

1. Installeer als aangepaste HACS-repository (`nelbs/woningwaarde`, categorie Integratie), zodra deze versie daar gepubliceerd is. Voor deze lokale versie: kopieer `custom_components/woningwaarde` naar de map `config/custom_components/woningwaarde` van Home Assistant.
2. Herstart Home Assistant.
3. Ga naar **Instellingen > Apparaten & diensten > Integratie toevoegen > Woningwaarde**.
4. Vul een blijvend woning-ID in (bijvoorbeeld `thuis`), een naam, regio, woningtype, bekende waarde in euro en de bijbehorende datum.
5. Voeg voor iedere volgende woning opnieuw Woningwaarde toe, met een ander woning-ID. Gelijke namen/prijzen zijn toegestaan.
6. Gebruik **Opnieuw configureren** in het integratiemenu om naam, regio, woningtype, prijs of datum aan te passen. Het woning-ID blijft gelijk, evenals de sensoridentiteit.

De sensor is numeriek, met valuta EUR. Iedere woning heeft een eigen apparaat en sensor met unieke ID. Attributen tonen de gekozen regio en het woningtype, CBS-tabellen, referentiewaarde en -datum, de gebruikte indices en groeifactoren en beide kwartalen. Bij een bronfout wordt de sensor niet beschikbaar; een oude waarde wordt niet als actuele waarde aangeboden.

## Berekening en dekking

`waarde = bekende waarde * groei_woningtype * groei_regio / groei_Nederland`

Iedere groeifactor is de verhouding van twee CBS-indexstanden; dezelfde datums of kwartalen worden gebruikt voor alle drie reeksen. De landelijke woningtypeontwikkeling wordt gecorrigeerd voor de regionale ontwikkeling ten opzichte van Nederland. Dit is een **afgeleide gecombineerde schatting**, geen afzonderlijk door CBS gepubliceerde index voor het woningtype binnen die regio.

Via **Berekeningsmethode** kies je expliciet:

- **Kwartaal zonder prognose (oude methode):** de referentiedatum gebruikt de index van het kwartaal waarin hij ligt. De eindwaarde gebruikt het laatst gemeenschappelijk gepubliceerde kwartaal. Geen daginterpolatie of prognose. Bestaande configuraties behouden deze methode tot je zelf een andere kiest.
- **Datumberekening met prognose:** de index van een kwartaal wordt als modelconventie geplaatst op de eerste dag **na** dat kwartaal. Zo gebruikt 1 juli 2016 de index van kwartaal 2, niet kwartaal 3. Tussen aansluitende kwartaalgrenzen wordt lineair geinterpoleerd op basis van werkelijke kalenderdagen. Na de laatste gemeenschappelijke kwartaalgrens wordt de laatst waargenomen indexverandering lineair doorgetrokken, maximaal vier kalendermaanden. Ontbrekende kwartalen worden niet overbrugd. Nieuwe configuraties bieden deze methode als standaard aan.

Een kwartaalindex is geen door CBS gepubliceerde dagprijs. De datumberekening en het doortrekken van een trend zijn expliciete modelaannames. Na de laatste publicatie is `value` dus een prognose; `is_forecast`, `forecast_days`, `published_date`, `valuation_date` en `forecast_method` maken dit zichtbaar. `indexed_value` toont apart de waarde op de laatste gemeenschappelijke kwartaalgrens zonder extrapolatie. `indices` toont de referentie-, gepubliceerde en berekende eindindices.

Ontbreekt een noodzakelijke index, of ligt de prognosedatum meer dan vier maanden voorbij de laatste publicatie, dan meldt de integratie de ontbrekende gegevens in plaats van onbeperkt een oude trend door te trekken.

Regio en woningtype zijn afzonderlijke keuzes:

- Nederland, alle twaalf provincies en de vier grote gemeenten Amsterdam, Den Haag, Rotterdam en Utrecht (85792NED).
- Alle woningtypen, eengezinswoning, tussenwoning, hoekwoning, twee onder een kap, vrijstaand of appartement (85791NED).

Bij **Alle woningtypen** vervalt de woningtypecorrectie en volgt de uitkomst de regionale index. Bij regio **Nederland** volgt de uitkomst alleen de woningtype-index. Voor andere gemeenten kies je de provincie. De uitkomst is geen individuele taxatie of actuele WOZ-waarde.

### Vergelijking met BerekenHet

Een fictieve controleberekening bij BerekenHet (18 oktober 2026; Gelderland, twee onder een kap, EUR 250.000 op 01-01-2020, gevraagd 01-07-2026) toonde regionale, landelijke en woningtypewaarden van respectievelijk EUR 435.500, EUR 408.200 en EUR 413.200, met een gecombineerde uitkomst EUR 440.800. De verhouding `413200 * 435500 / 408200` rondt af op dezelfde uitkomst. Dit ondersteunt de gebruikte multiplicatieve correctie. Het is geen volledige reconstructie van de niet-gepubliceerde BerekenHet-formule.

De precieze verwerking van datums door BerekenHet is niet volledig gereconstrueerd; de site beschrijft wel extrapolatie na de laatste publicatie. Deze integratie gebruikt de huidige CBS-reeks. De oude kwartaalmethode stopt bij de publicatie; de nieuwe datummethode interpoleert en extrapoleert expliciet. Een identieke uitkomst als BerekenHet wordt niet beloofd: ook de historische bronreeksen verschillen. Zie de analyse hieronder.

## Frequentie en netwerkbelasting

Iedere woningcoordinator controleert lokaal eens per uur. Dit herberekent met de opgeslagen gegevens en controleert of de broncache verlopen is; het betekent niet dat er ieder uur een CBS-verzoek wordt gedaan. Alle woningen delen dezelfde **op schijf opgeslagen** cache van de twee CBS-tabellen. Per gebruikte tabel wordt hoogstens eens per 24 uur een nieuwe ophaalpoging gedaan, ook bij herladen, herstarten, handmatig bijwerken of een bronfout. Woningen die dezelfde tabel gebruiken veroorzaken geen extra CBS-verzoeken. Per tabel is normaal een GET nodig; bij CBS-paginering worden vervolgpagina's binnen dezelfde poging opgehaald. Alleen gebruikte tabellen worden opgehaald. Het verwijderen van de cache of een tweede HA-installatie valt buiten deze limiet.

HTTP-time-out: 30 seconden per verzoek, 60 seconden voor de hele ophaalpoging. Geen automatische netwerkretry binnen de 24 uur; na een mislukte poging volgt de eerstvolgende toegestane netwerkpoging na 24 uur, normaal bij een lokale controle binnen het daaropvolgende uur. De API ontvangt geen woningnamen, adressen of prijzen. De configuratie en cache worden lokaal door Home Assistant opgeslagen.

## Overstappen van versie 0.x (YAML)

Deze versie vervangt de oude YAML-sensor; automatische conversie is niet inbegrepen.

1. Bewaar je bestaande naam, `waarde`, `datum`, `region` en `type`.
2. Verwijder de oude `- platform: woningwaarde` uit de `sensor:`-configuratie.
3. Installeer de nieuwe bestanden, herstart en voeg iedere woning via de interface toe.
4. Zet de oude datum `dd-mm-jjjj` om naar de datumkiezer. Kies expliciet de regio en het woningtype. Bijvoorbeeld de oude regio Gelderland en type `2onder1kap` worden nu Gelderland en twee onder een kap.
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

## Prerelease v1.0.1b4: regio en woningtype combineren

Regio en woningtype kunnen nu tegelijk ingesteld worden via **Opnieuw configureren**. De gecombineerde schatting volgt de hierboven beschreven regionale correctie.

Configuraties uit b1-b3 blijven werken zonder opnieuw toevoegen: een oude regionale keuze blijft dezelfde regio met **Alle woningtypen**; een oude woningtypekeuze blijft dat type met regio **Nederland**. Er wordt geen woningtype voor je geraden. Kies via Opnieuw configureren zelf de gewenste combinatie. De sensoridentiteit blijft behouden.

De standaardberekening is nu de gecombineerde formule, met beide groeifactoren en hun landelijke correctie zichtbaar in de sensorattributen. De dagelijkse cachelimiet en het icoon blijven behouden. Werk via HACS bij naar `v1.0.1b4` en herstart Home Assistant.

## Prerelease v1.0.1b5: datumverwerking en prognose

**Onderzocht op 22 oktober 2026, zonder factoren te fitten.** Zie [de volledige analyse](docs/analysis-2026-10-22.md).

Voor Limburg, twee onder een kap, EUR 309.000 op 1 juli 2016 en als einddatum 22 oktober 2026:

| Berekening met actuele CBS PBK2020 | Waarde |
| --- | ---: |
| Oude kwartaalmethode | EUR 607.441,75 |
| Referentiedatum op juiste kwartaalgrens volgens de nieuwe datumconventie, einddatum 1 oktober | EUR 616.406,46 |
| Datumberekening met lineaire prognose tot 22 oktober | EUR 618.011,05 |
| BerekenHet volgens screenshot en eigen controle | EUR 622.900 |

De historische BerekenHet-grafiekpunten tot en met 1 januari 2024 sluiten aan op de gearchiveerde PBK2015-reeks. Alle 31 gecontroleerde punten per regio/landelijk/type (93 punten totaal) komen overeen binnen de normale afronding op EUR 100. De huidige PBK2020-reeks bevat herziene historische prijsverhoudingen. De overgang/afronding van BerekenHet na 2023 is niet volledig gereconstrueerd. De resterende afwijking wordt daarom niet met een schaalfactor of een onverklaarde koppeling tussen reeksen weggewerkt.

**Bijwerken:** installeer `v1.0.1b5` via HACS, herstart en kies bij **Opnieuw configureren > Berekeningsmethode > Datumberekening met prognose**. De standaard voor bestaande configuraties blijft de oude kwartaalmethode totdat je zelf wisselt. De woning- en sensoridentiteit blijven behouden. De dagelijkse broncache blijft ongewijzigd; publicaties kunnen daardoor maximaal circa 24 uur later worden opgehaald. Controleer `latest_period` als je met een zojuist gepubliceerde CBS-tabel vergelijkt.

## Prerelease v1.0.1b6: lokale controle en broncache apart plannen

De lokale controle vindt nu eens per uur plaats, terwijl de harde limiet voor CBS-ophaalpogingen **24 uur per tabel** blijft. Dit voorkomt dat een fractie te vroeg geplande dagelijkse HA-update de broncache nog net geldig vindt en daarna nog een hele dag wacht. Home Assistant rondt het moment van de coordinatorupdate af; een exact gelijke lokale interval en cacheduur waren daarom geen betrouwbare combinatie.

Nieuwe sensorattributen:

- `last_checked`: het tijdstip waarop de laatste lokale berekening geslaagd is (ISO-tijd met UTC-offset). Dit bewijst geen nieuw CBS-verzoek.
- `source_cache`: per CBS-tabel `last_attempt` en `next_attempt_eligible`, eveneens met UTC-offset. De tweede tijd is het vroegste toegestane tijdstip, geen garantie dat er precies dan een verzoek plaatsvindt. Bij ingeschakelde automatische polling volgt normaal binnen het volgende uur een controle.

Bijwerken: installeer `v1.0.1b6` via HACS en herstart Home Assistant. Een verlopen cache wordt bij het starten opgehaald; een nog geldige cache blijft gerespecteerd. Controleer daarna `last_checked`, `source_cache` en `latest_period`. De rekenformule en de keuze voor kwartaalmethode of prognose zijn niet veranderd.

De op 23 oktober gemelde attributen tonen alleen dat de laatste geslaagde berekening nog 22 oktober en kwartaal 2 gebruikte. Zonder runtimelog en het toenmalige tijdstip kan niet bewezen worden dat precies deze timingfout de oorzaak in die installatie was; de aangetoonde fout in de code is wel verholpen. Blijft ook `last_checked` stilstaan, controleer dan automatische polling en de Home Assistant-logboeken.
