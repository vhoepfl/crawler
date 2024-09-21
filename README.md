## Übersicht

Der Crawler nimmt eine Startseite als Eingabe, ausgehend von welcher alle Seiten der Website durchlaufen werden. Dabei wird jede einzelne Seite zum einen als HTML-Datei abgespeichert, zum anderen wird der Text auf der Website je nach gewählten Einstellungen bereinigt und zusammen mit einigen Metadaten in eine .txt-Datei gespeichert. 

## Aktuelle Limits
Wenn die gewählte Website CAPTCHAS oder ähnliche Maßnahmen verwendet, um automatisierte Zugriffe zu blockieren, funktioniert der Crawler zwar, kann allerdings keinen relevanten Text extrahieren und bricht nach kurzer Zeit ab, da keine neuen Links mehr gefunden werden können. 
Je nach CAPTCHA-Typ könnte es möglich sein, das automatisch zu umgehen. Ich gehe allerdings davon aus, dass es am Ende am einfachsten wäre, playwright zu verwenden und dort die CAPTCHAS von Hand zu lösen - falls dieses Problem tatsächlich aufkommen sollte (*nach Erfahrung bei über 50 Seiten nicht*), würde ich mich hier nochmal genauer informieren.<br>

Außerdem begrenzen einige Webseiten die Zahl an Zugriffen auf die Seite insgesamt bzw. sperren den Crawler, wenn zu viele Zugriffe in zu kurzer Zeit erfolgen.
Dies ist tendenziell daran erkennbar, dass (bei Verwendung von [requests](#dynamisch-generierte-websites)) alle Webseitenaufrufe einen Fehler zurückgeben, oder (bei Verwendung von [playwright](#dynamisch-generierte-websites)) kein Webseitentext mehr gefunden wird. 

**robots.txt** 
Die meisten Internetseiten haben unter `seitenname.xyz/robots.txt` genauere Informationen darüber, welche automatisierten Zugriffe zugelassen werden und welche unerwünscht sind. 
Aktuell besitzt der Crawler nicht die Funktion, auf diese Datei zuzugreifen und die Einschränkungen automatisch zu berücksichtigen, dies könnte allerdings relativ problemlos umgesetzt werden, falls hier Bedarf besteht. 

An sich kann die `robots.txt` problemlos ignoriert werden, dies erhöht allerdings das Risiko, dass der Zugriff auf die Seite blockiert wird. <br> 
Falls dies passiert, könnte es helfen, die WLAN-Verbindung aus- und wieder einzuschalten, da dann (zumindest in eduroam) vermutlich eine neue IP-Adresse zugewiesen wird, sowie beim nächsten Versuch in den Einstellungen `playwright` auf `True` und **`delay` auf einen höheren Wert** (idealerweise jenen, der in der `robots.txt` angegeben wird) zu setzen. Siehe den [folgenden Teil](#dynamisch-generierte-websites) für mehr Details. 

Außerdem enthält die `robots.txt` Informationen  darüber, welche Teile der Seite nicht gecrawlt werden sollen. 
Diese können durch die [`pages_to_be_ignored`-Option](#general) gesperrt werden. 

## Dynamisch generierte Websites
Aktuell unterstützt der Code zwei verschiedene Möglichkeiten, auf die Seiten zuzugreifen: 
- **requests**<br>
Basismethode, um auf statische Websites zuzugreifen. Schneller als playwright sowie mit genaueren Fehlermeldungen - führt allerdings nur eine einzelne GET-Anfrage auf die Website aus und bekommt damit nur jenen Websiteninhalt zurück, welcher sofort zu Beginn geladen wird. 
- **playwright**<br>
Playwright öffnet ein echtes Browserfenster, um auf die Website zuzugreifen, und lädt die Seite wie sie auch in einem normalen Browser dargestellt wird. 

Anschließend scrollt der Browser vollständig nach unten, um alle dynamisch generierten Elemente (z.B. Artikel, die erst erscheinen, wenn nach unten gescrollt wird) zu laden. 
[`delay`](#general) regelt dabei die Zeitspanne, welche abgewartet wird, um der Seite Zeit zu geben zum Laden neuer Elemente. 

Darüber hinaus können in diesem Modus verschiedene Buttons festgelegt werden, auf welche automatisch geklickt wird (z.B. für *Afficher plus*, Details siehe unter [general](#general))


## Setup
Um den Crawler auszuführen, muss eine aktuelle python-Version installiert sein (getestet mit python3.10). Außerdem sind einige libraries notwendig, die wie folgt installiert werden können: 
`pip install pyyaml requests bs4 html2text`

Playwright kann mit `pip install playwright` installiert werden. <br> 
Anschließend können dann verschiedene Browser heruntergeladen werden mit `playwright install`. <br>
Details auf der [playwright-Website](https://playwright.dev/python/docs/intro). 

Darüber hinaus müssen die Dateien aus diesem github repository heruntergeladen werden. Dies geht entweder per Download über den Browser, oder idealerweise - wenn `git` installiert ist - indem im Terminal `git clone https://github.com/vhoepfl/crawler.git` ausgeführt wird. 

Der Code kann anschließend in einem Terminal ausgeführt werden, indem man mit `cd crawler` in das repository geht und ```python crawler\run_crawler.py``` ausführt . 

Dann beginnt ein hoffentlich relativ selbsterklärender Abfrageprozess, in welchem der gewünschte Speicherordner sowie die Zielwebsite eingegeben werden können. 
Darüber hinaus wird im Speicherordner eine `settings.yaml`-Datei angelegt, in welcher vor Beginn die gewünschten Einstellungen für den Crawler angepasst werden können -  mehr Infos hierzu stehen im [letzten Teil dieses Texts](#einstellungen). 


## Visualisierung

Während der Crawler läuft, wird der Verlauf im Terminal visualisiert. 
Die Darstellung entspricht keinen absoluten Zahlen, sondern zeigt jeweils das Verhältnis zwischen den bereits besuchten Seiten (sowie die Qualität der extrahierten Texte) und jenen, die sich noch in der Warteschlage befinden. 

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

Bei playwright erfolgt aus technischen Gründen keine detaillierte Fehlermeldung. 
Falls die Seite überhaupt nicht geladen werden kann, wird eine Fehlermeldung wie folgt ausgegeben: 
```
Unknown exception on *URL*: Page.goto: Timeout 240000ms exceeded.
```
Falls die Seite zwar geladen werden kann, aber keine gültige Antwort gibt, wird sie einfach als leere Seite ohne Text geladen (und kann mit dem Filter *word_count_limit* ignoriert werden)

## Ausgabe: 
Der Crawler schreibt in dem neu erstellten Ordner Daten in 4 Dateien: 
- `all_pages_html.txt`: Der HTML-Code aller besuchten Seiten (unabhängig davon, ob Text extrahiert wurde) kombiniert in einer txt-Datei getrennt durch `--- Separator ---`. 
- `console_output.log`: Eine Version der Ausgabe im Terminal, die die besuchten URLs und den Erfolg der jeweiligen Textextraktion notiert. 
- `scraped_pages_*Seitenname*.txt`: Die extrahierten Metadaten und der Webseitentext. 
- `settings.yaml`: Die Datei mit den Einstellungen, die zu Beginn bearbeitet werden kann. 


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
  Hier können URLS oder Teile davon angegeben werden, welche ignoriert werden sollen. <br>
  Es kann Regex verwendet werden, d.h.  `https://argosfrance.org/\d+` ignoriert z.B. `https://argosfrance.org/1`, `https://argosfrance.org/2`, `https://argosfrance.org/10` usw. 
  Außerdem reicht es, einzelne Wörter anzugeben, um jede URL auszuschließen, die diese Wörter enthält. 
  So blockiert `#comments` z.B. jede URL, die dieses Wort enthält, also bespielsweise alle Kommentarseiten zu einem Artikel. 

  Da Regex `\` und `/` als Sonderzeichen interpretiert, müssen diese normalerweise escaped werden. Dies passiert hier automatisch, es kann einfach eine URL oder Teil-UR n die *settings*-Datei kopiert werden und mit verschiedenen Regex-wildcards wie `.*`kombiniert werden. <br><br>
  Bitte die verschiedenen Wörter in Form einer Liste angeben (Beispiel siehe **click-buttons**)! <br>

  **Bei dieser Option (und nutr dort) können zur `settings.yaml`-Datei auch noch weitere Wörter hinzugefügt werden, während der Crawler läuft.** Einmal pro Minute wird kontrolliert, ob sich neue Elemente in dieser Liste befinden. 
  Falls ja, werden diese URLs zukünftig blockiert und alle entsprechenden URLs aus der Warteschlange gelöscht. 


### ```metadata```
- #### ```date```
  - `use_fallback_method: True`
  Die *fallback method* kann verwendet werden, falls der `head` im HTML-Code der Website kein Datumselement enthält. Falls diese Option auf `True` gesetzt ist, wird dann der vollständige Text der Website nach einem datumsähnlichen string durchsucht. <br><br>
  **Anmerkung:** 
  Dies kann falsche Ergebnisse produzieren, falls auf der Website ein beliebiges anderes Datum über dem oder statt des Artikeldatums steht. Aus diesem Grund wird ein solches Datum mittels `⚠` im Terminaloutput und in Log hervorgehoben (allerdings nicht im endgültigen Textoutput). 
  Hier wäre es möglich, im Nachhinein zu kontrollieren, ob die Datümer in einem zeitlich plausiblen Rahmen liegen. 
  <br><br>  

  - Optional gibt es die Möglichkeit, nach einem spezifischen Datumselement im HTML-Code zu suchen. Dies geschieht über die folgenden 3 Variablen: 
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

    Falls das Datumselement selbst als `name`-Wert eines `attrib` vorliegt, reicht es, `tag`und `attrib` anzugeben. 
    **Beispiel:** <br>
    `<span datetime="2009-05-28T17:51:00+02:00"` <br>
      ```
      tag: span
      attrib: datetime
      ``` 

- #### `title` <br>
  - Äquivalent zu [date](#date)


- #### `author`
  - Äquivalent zu [date](#date)

- #### `volume`
  **Anmerkung: Da *Volume* sehr fehleranfällig ist, wird das Ergebnis aktuell nicht in der fertigen Ausgaben gespeichert!**

  Da scheinbar nur selten bis nie ein eigenes HTML-Element für das volume existiert, wird auf eine ähnliche Methode wie bei der *fallback method* für das Datum zurückgegriffen: Jede volume-ähnliche Nummerierung (z.B. `N. <Zahl>`, `Vol. <Zahl>`, `Éd. <Zahl>` - der Punkt ist dabei optional ) wird als volume interpretiert und gespeichert. <br>
  Das Format aus einer Zahl und einem Punkt, z.B. `1.`, wird aktuell nicht als volume erkannt, da hier die Fehleranfälligkeit vermutlich zu hoch ist. 

  - `extract_volume: True`
      Falls auf `True` gesetzt, wird ein volume auf die oben beschriebene Weise extrahiert. 


### `text_extraction`
Auf welche Weise wird der Websitentext extrahiert? 
- #### `only_paragraphs: True`
  Falls auf `True`gesetzt, wird Text nur aus `<p>`-tags extrahiert. Diese Option ignoriert relativ aggressiv weite Teile der Webseite, daher nur eingeschränkt zu empfehlen. 
- #### `only_paragraphs_and_headers: True`
  Falls auf `True`gesetzt, wird Text nur aus aus Überschriften (d.h. `<h1>` bis `<h6>`) und `<p>`-tags extrahiert. Weniger extrem als *only_paragraphs*, allerdings trotzdem sehr unselektiv, diese Option auf `False` zu setzen und gezielt Elemente anzugeben ist daher sinnvoller, wo immer möglich. 
- #### `specific_tags_include`: 
    - Mittels dieser Option können wie bei [metadata](#metadata) spezifische Elemente oder Attribute festgelegt werden, *aus welchen der Text extrahiert wird* - der Rest des Websitentexts wird dann ignoriert. 
      ```
      specific_tags: 
        - tag:
          attrib: 
          name: 
      ```
  - **Mehrere Formate/Strukturen gleichzeitig suchen**<br>
    Technisch gesehen ist `tag:_, attrib:_, name:_`ein dictionary, welches als einzelnes Element einer Liste abgespeichert wird. Es kann also nach mehreren Blöcke aus tag, class, id gleichzeitig gesucht werden, indem jeweils ein Bindestrich davor platziert wird: 
      ```
      specific_tags: 
        - tag:
          attrib: 
          name: 
        - tag:
          attrib: 
          name: 
        - ...
      ```
    **Nach jeder Kombination (tag, attrib, name) wird dabei unabhängig von den anderen gesucht.** <br><br>
  
  - **Es ist nicht notwendig, für alle drei Elemente einen Wert         anzugeben.**
      ```
      <article id="post-52228" class="post_item_single post_type_post post_format_ post-52228 post type-post status-publish format-standard has-post-thumbnail hentry category-communiques">
      ``` 
    wird also von allen der folgenden Kriterien erkannt: 
      ```
      specific_tags: 
        - tag: article
          attrib: class
          name: post_item_single # Oder auch ein oder mehrere andere von *post_type_post, post_format_ post-52228, ...*
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
          attrib: class
          name: post_item_single # Oder auch ein oder mehrere andere von *post_type_post, post_format_ post-52228, ...*
      ```
  

 - `specific_tags_exclude`: Mittels dieser Option können spezifische Elemente oder Attribute festgelegt werden, *aus welchen KEIN Text extrahiert wird* - alle angebenen Elemente werden ignoriert. 
    - Verwendbar zum Beispiel für Impressumtext, oder für Links zu Social Media. <br>
    - Funktioniert genau wie `specific_tags_include`. 

  <br>  

  **Es kann sein, dass innerhalb einer Website kein kohärentes System für die Strukturierung der Seite existiert**  - beispielsweise indem mehrere unterschiedliche Werte für `name` wie *article-iliade* und *articleiliade* parallel verwendet werden. In diesem Fall wäre es wichtig, alle Optionen anzugeben, da sonst der Text einiger Seiten relativ spurlos ignoriert wird. Die einzige Möglichkeit, dies festzustellen, ist zum einen, mehrere Seiten aus verschiedenen Kategorien zu durchsuchen und alle relevanten Formate zu notieren, und zum anderen manuell die logging-Datei durchzugehen und für Dateien mit auffällig niedrigen *percentage*-Werten zu kontrollieren, ob hier ein anderes Format verwendet wird. 

<br>

### `output`
- #### `console`
  - `verbose`
  Falls `True`, werden während des crawlen zusätzliche Infos ausgegeben
  - `print_one_per: 1`
  Zahl *n* von 1 bis unendlich: Einmal pro *n* gecrawlten Seiten werden Infos ausgegeben. 
- #### `file`
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
  Automatische Entfernung von Webseiten mit unterschiedlichen URLs aber **identischem Inhalt**. <br>
  - Mittels `threshold_value` kann angegeben werden, wie viel Prozent Überlappung gegeben sein müssen, damit die Seite ignoriert wird. 


## Hinweise/Erfahrungen aus dem Scraping
- **Artikelvorschau:** Oftmals wird dasselbe tag, welches Artikel markiert, auch für kleine Artikelvorschautexte verwendet, was unerwünschten Text bringt
- **Dynamisch generierte Websites:** Falls eine Seite beim nach-unten-Scrollen noch weitere Inhalte lädt, muss playwright verwendet werden. 