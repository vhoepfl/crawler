## Crawler Prototype

### How to run the code? 
Before running the code, some libraries have to be installed: 
- pyyaml
- requests
- bs4

All of those can be installed via pip. 


Then execute the code with
```python run_crawler.py```. 

A relatively self-explanatory setup process is then started. 

[Explanatation of my choices : ]<br>Here, the plan is to use one folder for one website for easier organisation of the scraped data, settings and logs. This is why an existing folder cannot be used without overwriting of its contents. <br>
While there is the option to specify further settings in the settings file in the newly created folder (e.g. if only paragraphs are to be used when scraping the text, or if only specific html tags should be included), everything runs also without changing anything. 

Defaults: 
- Text: Anything scraped 
- Date: Taken from standard (?) tag in file head, otherwise ignored
- Title: Taken from standard (?) tag in file head, otherwise ignored

## Visualization

There is a sick visualization counting the scraped pages and the current queue :) 

Legend: 
| symbol    | meaning |
| -------- | ------- |
| -  | neither title nor date found    |
| D | Date found but not title |
| T    | Title found but not date |
| ░ | Under 30 % of page extracted | 
|▒ | Between 30 and 60 % of page extracted |
|▓ | Over 60 % of page extracted 

Here the percent numbers refer only to those pages, where both date and title were found, since only those are likely to be articles

todo: maybe category for nothing extracted
## Current limitations
- The scraped data is not saved anywhere, but I'm not sure yet how to do this the best way
- The robots.txt is currently ignored, but most of the pages don't specify limitations anyways, and who cares
- All of this is relatively slow at the moment. I suppose this is due to the parser used for the html page. Here, it would be possible to use a faster parser, but currently the slower default parser is used. <br>
- Possible optimization: Only parsing first 50(?) lines and checking if date + title is available (No idea if this would work)