## Übersicht

Der Crawler nimmt eine Startseite als Eingabe, ausgehend von welcher alle Seiten der Website durchlaufen werden. Dabei wird jede einzelne Seite zum einen als HTML-Datei abgespeichert, zum anderen wird der Text auf der Website je nach gewählten Einstellungen bereinigt und zusammen mit einigen Metadaten in eine .txt-Datei gespeichert. 

## Aktuelle Limits
Wenn die gewählte Website CAPTCHAS oder ähnliche Maßnahmen verwendet, um automatisierte Zugriffe zu blockieren, funktioniert der Crawler zwar, kann allerdings keinen relevanten Text extrahieren und bricht nach kurzer Zeit ab, da keine neuen Links mehr gefunden werden können. 
Je nach CAPTCHA-Typ könnte es möglich sein, das automatisch zu umgehen. Ich gehe allerdings davon aus, dass es am Ende am einfachsten wäre, den Crawler mit einem playwright-Browser zu kombinieren und die CAPTCHAS von Hand zu lösen - falls dieses Problem tatsächlich aufkommen sollte, würde ich mich hier nochmal genauer informieren.<br>
**robots.txt** 
Die meisten Internetseiten haben unter `seitenname.xyz/robots.txt` genauere Informationen darüber, welche automatisierten Zugriffe zugelassen werden und welche unerwünscht sind. 
Aktuell besitzt der Crawler nicht die Funktion, auf diese Datei zuzugreifen und die Einschränkungen automatisch zu berücksichtigen, dies könnte allerdings relativ problemlos umgesetzt werden, falls hier Bedarf besteht. 

An sich kann die `robots.txt` problemlos ignoriert werden, dies birgt allerdings das Risiko, dass der Zugriff auf die Seite blockiert wird. 
Falls dies passiert, könnte es helfen, die WLAN-Verbindung aus- und wieder einzuschalten, da dann (zumindest in eduroam) vermutlich eine neue IP-Adresse zugewiesen wird, sowie beim nächsten Versuch in den Einstellungen `playwright` auf `True` und `delay` auf einen Wert > 0 zu setzen. Siehe den [folgenden Teil](#dynamisch-generierte-websites) für mehr Details. 

## Dynamisch generierte Websites
Aktuell unterstützt der Code zwei verschiedene Möglichkeiten, auf die Seiten zuzugreifen: 
- **requests**<br>
Basismethode, um auf statische Websites zuzugreifen. Schneller als playwright sowie mit genaueren Fehlermeldungen - führt allerdings nur eine einzelne GET-Anfrage auf die Website aus und bekommt damit nur jenen Websiteninhalt zurück, welcher sofort zu Beginn geladen wird. 
- **playwright**<br>
Playwright öffnet ein echtes Browserfenster, um auf die Website zuzugreifen, und scrollt dann in mehreren Schritten bis nach unten. `delay`ist dabei die Wartezeit, während der die Seite laden kann, und nach deren Ablauf überprüft wird, ob noch neuer Inhalt lädt oder die Seite vollständig ist. Es können verschiedene Buttons festgelegt werden, auf welche automatisch geklickt wird (z.B. für *Afficher plus*, Details siehe unter [general](#general))


## Setup
Um den Crawler auszuführen, muss eine aktuelle python-Version installiert sein (getestet mit python3.10). Außerdem sind einige libraries notwendig, die wie folgt installiert werden können: 
`pip install pyyaml requests bs4`
Playwright kann mit `pip install playwright` installiert werden. <br> 
Anschließend können dann verschiedene Browser heruntergeladen werden mit `playwright install`. <br>
Details auf der [playwright-Website](https://playwright.dev/python/docs/intro). 

Darüber hinaus müssen die Dateien aus diesem github repository heruntergeladen werden. Dies geht entweder per Download über den Browser, oder idealerweise - wenn `git` installiert ist - indem im Terminal `git clone https://github.com/vhoepfl/crawler.git` ausgeführt wird. 


Der Code kann anschließend in einem Terminal ausgeführt werden, indem man mit `cd crawler` in das repository geht und ```python crawler\run_crawler.py``` ausführt . 
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

## Timeouts/Verbindungsabbruch
Falls die Verbindung abbricht (oder die Seite nicht lädt), wird das Laden der Seite nach einiger Zeit abgebrochen und die Seite verworfen. Dies wird mit einer Warnmeldung im Terminal und im Log angezeigt: 
```
WARNING: Request timed out on https://terreetpeuple.com/plan-de-site.html?view=html&id=1
```
Falls die Seite keine gültige Antwort zurückgibt (d.h. der Statuscode ist nicht 200), wird bei requests der Fehlercode ausgeben, im Log festgehalten und die Seite verworfen. 
```
Error when loading page https://terreetpeuple.com/affiche_liste.php?dpt=81: 404
```
Bei playwright erfolgt aus technischen Gründen keine spezielle Fehlerbehandlung, die Seite wird einfach als leere Seite geladen. 
 
## Einstellungen
Im Speicherordner wird automatisch eine *settings.yaml*-Datein angelegt. Dort können zu Beginn die Einstellungen für den Scraping-Prozess festgelegt werden. <br>
Im Folgenden werden die verschiedenen Optionen genauer erklärt: 
### ```general```
- `playwright: False`
Falls `True`, wird ein playwright-Browser anstatt requests verwendet. Dies erhöht Websiteladezeiten signifikant, ist aber notwendig, um dynamisch generierte Websites korrekt zu scrapen oder Buttons zu klicken, da ansonsten nur ein Bruchteil der Seite geladen ist und entsprechend gescraped wird. 
- `delay: 0` 
Bei Verwendung von Playwright, ansonsten ignoriert: Wartezeit (in ms) zwischen zwei Aufrufen. Idealerweise lang genug, um die Seite vollständig zu laden, aber dabei so kurz wie möglich. 
- `click_buttons`
Hier können mehrere Buttons angegeben werden, auf welche automatisch geklickt wird. <br>
Anzugeben entweder als `button.Klasse` (da jeder button immer `button` als tag hat) oder auch nur `.Klasse`. <br>
Beispiel: <br>
**`button.eael-load-more-button`** für `<button class="eael-load-more-button hide-load-more" id="eael-load-more-btn-3f26d46"... `<br><br>
Bitte immer nur eine der Klassen angeben! <br>
Bitte als Liste angeben, d.h. 
  ```
  click_buttons: 
    - button.eael-load-more-button
    - button.close-popup
    - ...
  ```
- `pages_to_be_ignored`
Hier können URLS angegeben werden, welche ignoriert werden sollen. <br>
Es kann Regex verwendet werden, d.h.  `https://argosfrance.org/boutique.*` ignoriert z.B. `https://argosfrance.org/boutique/#`, `https://argosfrance.org/produit/softshell-bleu-marine-argos/` etc. (`.*` steht für eine beliebige Zahl an beliebigen Zeichen) <br>
Da Regex `\` und `/` als Sonderzeichen interpretiert, müssen diese normalerweise escaped werden. Dies passiert hier automatisch, es kann einfach eine URL in die *settings*-Datei kopiert werden und mit verschiedenen Regex-wildcards wie `.*`kombiniert werden. <br><br>
Bitte die verschiedenen URLS in Form einer Liste angeben (Beispiel siehe **click-buttons**)! <br>


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

**Beispiel:** <br>
`<meta property="article:published_time" content="2024-04-02T16:09:32+00:00">`<br>
Das Datumselement wird über die folgenden 3 Werte identifiziert und `content` anschließend auf jeder Seite automatisch extrahiert: 
  ```
  tag: meta
  attrib: property
  name: article:published_time
  ```

Alternativ reicht auch nur das tag: <br>
**Beispiel:** <br>
`<date_published>05 juillet 2024</date_published>` <br>
  ```
  tag: date_published
  ```

#### `title`
Die folgenden 3 Variablen (oder auch nur tag) identifizieren das Titelelement im HTML-Code. Der Crawler läuft auch, wenn hier keine Werte angegeben sind, allerdings wird dann kein Titel gefunden.  Siehe das Datumselement `date` oberhalb für ein Beispiel der Funktionsweise. 


#### `author`
Siehe `date` für die Funktionsweise 

#### `volume`

Da scheinbar nur selten bis nie ein eigenes HTML-Element für das volume existiert, wird auf eine ähnliche Methode wie bei der *fallback method* für das Datum zurückgegriffen: Jede volume-ähnliche Nummerierung (z.B. `N. <Zahl>`, `Vol. <Zahl>`, `Éd. <Zahl>` - der Punkt ist dabei optional ) wird als volume interpretiert und gespeichert. <br>
Das Format aus einer Zahl und einem Punkt, z.B. `1.`, wird aktuell nicht als volume erkannt, da hier die Fehleranfälligkeit vermutlich zu hoch ist. 

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
      - tag:
        class: 
        id: 
    ```
    
    **Mehrere Formate/Strukturen gleichzeitig suchen**<br>
    Technisch gesehen ist `tag:_, class:_, id:_`ein dictionary, welches als einzelnes Element einer Liste `- tag: ...` abgespeichert wird. Es können also mehrere Blöcke aus tag, class, id gleichzeitig extrahiert werden, indem jeweils ein Bindestrich davor platziert wird: 
    ```
    specific_tags: 
      - tag:
        class: 
        id: 
      - tag:
        class: 
        id: 
      - ...
    ```
    Nach jeder Kombination (tag, class, id) wird dabei unabhängig voneinander gesucht. 
    Beispielsweise würde 
    ```
    specific_tags: 
      - tag: article
        class: 
        id: 
      - tag: comment
        class: 
        id: 
      - ...
    ```
    alle Elemente finden, die sich in einem tag `<article...` oder einem tag  `<comment...` befinden. <br>
    Abgesehen davon, dass damit mehrere verschiedene Websitelemente extrahiert werden können, kann dies auch eingesetzt werden, falls mehrere Formate wie `article-iliade`und `articleiliade` parallel verwendet werden.<br><br>
    **Es ist nicht notwendig, für alle drei Elemente einen Wert anzugeben:**<br>
    Die drei Elemente werden kombiniert, d.h. es wird jeder Webseitenteil extrahiert, der mit jedem gegebenen Kriterium übereinstimmt. 
    ```
    <article id="post-52228" class="post_item_single post_type_post post_format_ post-52228 post type-post status-publish format-standard has-post-thumbnail hentry category-communiques">
    ``` 
    wird also von allen der folgenden Kriterien erkannt: 
    ```
    specific_tags: 
      - tag: article
        class: post_item_single # Oder auch post_type_post, post_format_ post-52228, ...
        id: post-52228
    ```
    ```
    specific_tags: 
      - tag: article
        class: 
        id: 
    ```
    ```
    specific_tags: 
      - tag: 
        class: post_item_single # Oder auch post_type_post, post_format_ post-52228, ...
        id: 
    ```
    *Anmerkung:* Wenn bei `class="..."` mehrere Stichwörter stehen, darf aktuell nur eines der Stichwörter als Klasse angegeben werden. Falls mehrere unabhängig voneinander gewählt werden sollen, bitte einen weiteren Block anhängen und dort angeben. <br>
    Für das spezifische Szenario, dass zwei oder mehrere Klassen *gleichzeitig* vorhanden sein sollen, könnte ich den Code anpassen, aktuell ist dies aber nicht möglich.
    ```
    specific_tags: 
      - tag: 
        class: 
        id: post-52228
    ```
    *Anmerkung:* Wenn `id` offensichtlich eine artikelspezifische ID ist, ist es nicht sinnvoll, hier einen Wert anzugeben, da dann nur ein einziger Artikel einen Treffer liefern würde. <br><br>
    **Details zu den Variablentypen:**
    `tag`, `class`und `id` unterscheiden sich an dieser Stelle teilweise von den Variablen für *date* und *title*. 
    - `tag` ist äquivalent
    - `class` nimmt spezifisch Bezug auf den Namen/Wert, den das `class`-Attribut besitzt
    - `id` nimmt spezifisch Bezug auf den Namen/Wert, den das `id`-Attribut besitzt. <br>
    **Beispiel:**
    `<article id="post-1882" class="post_item_single post_type_post post_format_ post-1882 post type-post ...`
      ```
      tag: article
      id: post-1882
      class: post_item_single post_type...
      ```
      Dabei wäre - wie oberhalb beschrieben - einer der Werte (z.B. `tag:article`) ausreichend, um das entsprechende HMTL-Element zu matchen

  **Es kann sein, dass innerhalb einer Website kein kohärentes System für die Strukturierung der Seite existiert**  - beispielsweise indem mehrere unterschiedliche Werte für `id` wie *article-iliade* und *articleiliade* parallel verwendet werden. In diesem Fall wäre es wichtig, alle Optionen anzugeben, da sonst der Text einiger Seiten relativ spurlos ignoriert wird. Die einzige Möglichkeit, dies festzustellen, ist zum einen, mehrere Seiten aus verschiedenen Kategorien zu durchsuchen und alle relevanten Formate zu notieren, und zum anderen manuell die logging-Datei durchzugehen und für Dateien mit auffällig niedrigen *percentage*-Werten zu kontrollieren, ob hier ein anderes Format verwendet wird. 

      

### `output`
#### `console`
- `verbose`
Falls `True`, werden während des crawlen zusätzliche Infos ausgegeben
- `print_one_per: 1`
Zahl *n* von 1 bis unendlich: Einmal pro *n* gecrawlten Seiten werden Infos ausgegeben. 
#### `file`
Filteroptionen für die Ausgabe des finalen Texts in eine Datei - können jeweils deaktiviert werden, indem der Wert auf *-1* gesetzt wird. 
- `percentage_limit` 
Zahl von 1 bis 100 - jede Seite, auf der mit den gewählten Einstellungen ein niedrigerer Prozentsatz des Gesamttext extrahiert wurde, wird ignoriert. <br>
*Anmerkung:* Ich bin mir unsicher, in welchen Fällen diese Begrenzung überhaupt Sinn macht, da an sich die Extraktion von weniger Text ja höhere Qualität dieses extrahierten Texts nahelegt. 
- `word_count_limit`
Gesamtzahl der Wörter pro Seite: Jede Seite mit weniger extrahierten Wörtern wird ignoriert. 
- `mean_line_lenght_limit`
 Durchschnittliche Zahl an Wörtern pro (Text-)Zeile über die gesamte Seite - jede Seite mit kürzeren Zeilen wird ignoriert. <br>
 *Anmerkung:* Diese Metrik hilft zwar, Seiten mit vielen Links / kurzen Zeilen mit wenig brauchbarem Text auszusortieren, allerdings wird es vermutlich stark von der spezifischen Seite abhängen, ob diese Metrik Sinn macht und welcher Wert jeweils gut funktioniert. 

- `doublons`
  Automatische Entfernung von Webseiten mit unterschiedlichen URLs aber identischem Inhalt. <br>
  Mittels `threshold_value` kann angegeben werden, wie viel Prozent Überlappung gegeben sein müssen, damit die Seite ignoriert wird. 


## Hinweise/Erfahrungen aus dem Scraping
- **Artikelvorschau:** Oftmals wird dasselbe tag, welches Artikel markiert, auch für kleine Artikelvorschautexte verwendet, was unerwünschten Text bringt
- **Dynamisch generierte Websites:** Falls eine Seite beim nach-unten-Scrollen noch weitere Inhalte lädt, muss playwright verwendet werden. 