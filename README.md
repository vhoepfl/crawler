## Übersicht

Der Crawler nimmt eine Startseite als Eingabe, ausgehend von welcher alle Seiten der Website durchlaufen werden. Dabei wird jede einzelne Seite zum einen als HTML-Datei abgespeichert, zum anderen wird der Text auf der Website je nach gewählten Einstellungen bereinigt und zusammen mit einigen Metadaten in eine .txt-Datei gespeichert. 

## Aktuelle Limits
Wenn die gewählte Website CAPTCHAS oder ähnliche Maßnahmen verwendet, um automatisierte Zugriffe zu blockieren, funktioniert der Crawler zwar, kann allerdings keinen relevanten Text extrahieren und bricht nach kurzer Zeit ab, da keine neuen Links mehr gefunden werden können. 
Je nach CAPTCHA-Typ könnte es möglich sein, das automatisch zu umgehen. Ich gehe allerdings davon aus, dass es am Ende am einfachsten wäre, den Crawler mit einem playwright-Browser zu kombinieren und die CAPTCHAS von Hand zu lösen - falls dieses Problem tatsächlich aufkommen sollte, würde ich mich hier nochmal genauer informieren.<br>
**robots.txt** 
Die meisten Internetseiten haben unter `seitenname.xyz/robots.txt` genauere Informationen darüber, welche automatisierten Zugriffe zugelassen werden und welche unerwünscht sind. 
Aktuell besitzt der Crawler nicht die Funktion, auf diese Datei zuzugreifen und die Einschränkungen automatisch zu berücksichtigen, dies könnte allerdings relativ problemlos umgesetzt werden, falls hier Bedarf besteht. 

An sich kann die `robots.txt` problemlos ignoriert werden, dies birgt allerdings das Risiko, dass der Zugriff auf die Seite blockiert wird. 
Falls dies passiert, könnte es helfen, die WLAN-Verbindung aus- und wieder einzuschalten, da dann (zumindest in eduroam) vermutlich eine neue IP-Adresse zugewiesen wird, sowie beim nächsten Versuch in den Einstellungen den `delay` zwischen Zugriffen hochzusetzen. 


## Setup
Um den Crawler auszuführen, muss python3 installiert sein. Außerdem sind einige libraries notwendig, die über pip installiert werden können: 
- pyyaml
- requests
- bs4

Darüber hinaus müssen die Dateien aus diesem github repository heruntergeladen werden. Dies geht entweder per Download über den Browser, oder idealerweise - wenn `git` installiert ist - indem im Terminal `git clone https://github.com/vhoepfl/crawler.git` ausgeführt wird. 


Der Code kann anschließend in einem Terminal ausgeführt werden mit ```python crawler/run_crawler.py```. 
Dann beginnt ein hoffentlich relativ selbsterklärender Abfrageprozess, in welchem der gewünschte Speicherordner sowie die Zielwebsite eingegeben werden können. 
Darüber hinaus wird im Speicherordner eine `settings.yaml`-Datei angelegt, in welcher die gewünschten Einstellungen für den Crawler angepasst werden können -  mehr Infos hierzu stehen im [letzten Teil dieses Texts](#einstellungen). 


## Visualisierung

There is a sick visualization counting the scraped pages and the current queue :) 

Die Visualisierung wird ebenfalls (teilweise) in ein Log im Speicherordner geschrieben, so dass im Nachhinein noch ein Überblick besteht, welche Seiten ausgewählt wurden, und welche Metadaten gefunden wurden.

Legend: 
| symbol    | meaning |
| -------- | ------- |
| -  | neither title nor date found    |
| D | Date found but not title |
| T    | Title found but not date |
| ░ | Under 30 % of page extracted | 
|▒ | Between 30 and 60 % of page extracted |
|▓ | Over 60 % of page extracted |
|*| In queue (not yet visited)|


Here the percent numbers refer only to those pages, where both date and title were found, since only those are likely to be articles
 
## Einstellungen
### ```general```
- `delay: 0` 
Beschreibt die Wartezeit zwischen zwei Aufrufen. Entspricht idealerweise dem Wert, welcher in der `robots.txt` angegeben ist. 

### ```metadata```
#### ```date```
- `use_fallback_method: True`
Die *fallback method* kann verwendet werden, falls der `head` im HTML-Code der Website kein Datumselement enthält. Falls diese Option auf `True` gesetzt ist, wird dann der vollständige Text der Website nach einem datumsähnlichen string durchsucht. 
**Anmerkung:** 
Dies kann falsche Ergebnisse produzieren, falls auf der Website ein beliebiges anderes Datum über dem oder statt des Artikeldatums steht. Aus diesem Grund wird ein solches Datum mittels `⚠` im Terminaloutput und in Log hervorgehoben (allerdings nicht im endgültigen Textoutput). 
Hier wäre es möglich, im Nachhinein zu kontrollieren, ob die Datümer in einem zeitlich plausiblen Rahmen liegen. 

Optional gibt es die Möglichkeit, nach einem spezifischen Datumselement im HTML-Code zu suchen. Dies geschieht über die folgenden 3 Variablen: 
- `tag`
- `attrib`
- `name`
**Beispiel:** 
`<meta property="article:published_time" content="2024-04-02T16:09:32+00:00">`
Das Datumselement wird über die folgenden 3 Werte identifiziert und `content` anschließend auf jeder Seite automatisch extrahiert: 
  ```
  tag: meta
  attrib: property
  name: article:published_time
  ```

#### `title`
Die folgenden 3 Variablen identifizieren das Titelelement im HTML-Code. Der Crawler läuft auch, wenn hier keine Werte angegeben sind, allerdings wird dann kein Titel gefunden.  Siehe das Datumselement oberhalb für ein Beispiel der Funktionsweise. 
- `tag`
- `attrib`
- `name`


#### `volume`

Da scheinbar nur selten bis nie ein eigenes HTML-Element für das volume existiert, wird auf eine ähnliche Methode wie bei der *fallback method* für das Datum zurückgegriffen: Jede volume-ähnliche Nummerierung (z.B. `N. <Zahl>`, `Vol. <Zahl>`, `Éd. <Zahl>` - der Punkt ist dabei optional ) wird als volume interpretiert und gespeichert. 
Das Format aus einer Zahl und einem Punkt, z.B. `1.`, wird nicht als volume erkannt, da hier die Fehleranfälligkeit vermutlich hoch ist. 

- `extract_volume: True`
    Falls auf `True` gesetzt, wird ein volume auf die oben beschriebene Weise extrahiert. 

### `text_extraction`
Auf welche Weise wird der Websitentext extrahiert? 
- `only_paragraphs: True`
Text nur extrahiert aus `<p>`-tags. Diese Option sollte (je nach Aufbau der Website!) die Qualität der Daten verbessern, da z.B. Banner, Links und ähnlich Elemente, die sich oft auf jeder Seite wiederholen, ignoriert werden. 
- `specific_tags`: 
Mittels dieser Option können spezifische Elemente oder Attribute festgelegt werden, aus welchen der Text extrahiert wird - der Rest des Websitentexts wird dann ignoriert. (überschreibt `only_paragraphs`)
    ```
    specific_tags: 
      - tag
      - class: 
      - id: 
    ```
    Die einzelnen Werte sind hier (anders als bei *date* und *title*) unabhängig voneinander. 
    Es is hier also möglich, nicht alle der Variablen zu belegen und beispielweise nur ein `tag` oder eine `class` anzugeben. Falls mehrere Werte angegeben werden, wird jedes HTML-Element extrahiert, für welches ein oder mehrere der spezifizierten Kriterien zutreffen. 
    Darüber hinaus können für jeden einzelnen Typ mehrere Werte angegeben werden, indem diese durch Kommata getrennt werden: `id: article-iliade, articleiliade`
    **Details zu den Variablentypen:**
    `tag`, `class`und `id` unterscheiden sich an dieser Stelle teilweise von den Variablen für *date* und *title*. 
    - `tag` ist äquivalent
    - `class` nimmt spezifisch Bezug auf den Namen/Wert, den das `class`-Attribut besitzt
    - `id` nimmt spezifisch Bezug auf den Namen/Wert, den das `id`-Attribut besitzt
    **Beispiel:**
    `<article id="post-1882" class="post_item_single post_type_post post_format_ post-1882 post type-post ...`
      ```
      tag: article
      id: post-1882
      class: post_item_single post_type...
      ```
      Dabei wäre - wie oberhalb beschrieben - einer der Werte (z.B. `tag:article`) ausreichend, um das entsprechende HMTL-Element zu matchen

  **Anmerkung:**
  Soweit ich gesehen habe, kann es sein, dass innerhalb einer Website kein kohärentes System für die Strukturierung der Seite existiert - beispielsweise indem mehrere unterschiedliche Werte für `id` wie *article-iliade* und *articleiliade* parallel verwendet werden. In diesem Fall wäre es wichtig, alle Optionen anzugeben, da sonst der Text einiger Seiten relativ spurlos ignoriert wird. Die einzige Möglichkeit, dies festzustellen, ist, manuell die logging-Datei durchzugehen und für Dateien mit auffällig niedrigen *percentage*-Werten zu kontrollieren, ob hier ein anderer Wert verwendet wird. 

      

### `output`
#### `console`
- `verbose`
Falls `True`, werden während des crawlen zusätzliche Infos ausgegeben
- `print_one_per: 1`
Zahl *n* von 1 bis unendlich: Einmal pro *n* gecrawlten Seiten werden Infos ausgegeben. 
#### `file`
Filteroptionen für die Ausgabe des finalen Texts in eine Datei - können jeweils deaktiviert werden, indem der Wert auf *-1* gesetzt wird. 
- `percentage_limit` 
Zahl von 1 bis 100 - jede Seite, auf der mit den gewählten Einstellungen ein niedrigerer Prozentsatz des Gesamttext extrahiert wurde, wird ignoriert
*Anmerkung:* Ich bin mir unsicher, in welchen Fällen diese Begrenzung überhaupt Sinn macht, da an sich die Extraktion von weniger Text ja höhere Qualität dieses extrahierten Texts nahelegt. 
- `word_count_limit`
Gesamtzahl der Wörter pro Seite: Jede Seite mit weniger extrahierten Wörtern wird ignoriert. 
- `mean_line_lenght_limit`
 Durchschnittliche Zahl an Wörtern pro (Text-)Zeile über die gesamte Seite - jede Seite mit kürzeren Zeilen wird ignoriert. 
 *Anmerkung:* Diese Metrik hilft zwar, Seiten mit vielen Links / kurzen Zeilen mit wenig brauchbarem Text auszusortieren, allerdings wird es vermutlich stark von der spezifischen Seite abhängen, ob diese Metrik Sinn macht und welcher Wert jeweils gut funktioniert. 