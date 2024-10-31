import pandas as pd
import re
import datetime
from remove_doublons import MinHashFilter

#filepath = '/home/hoepfl/hiwijob/Laura/crawler/cmpl/serviam_alvarium/scraped_pages_web_archive_org_web_20230321152834_serviam_alvarium_fr.txt'
filepath = '/home/hoepfl/hiwijob/Laura/crawler/cmpl/arts_enracines/scraped_pages_arts_enracines_fr.txt'
date_format = ''


with open(filepath, 'r') as fr: 
    indiv_pages = re.findall('<begin-of-url>([\s\S]*?)<end-of-url>', fr.read())

url = []
title = []
date = []
author = []
text = []
for i in indiv_pages: 
    parts = i.split('<separate-parts>\n')
    url.append(parts[0].strip() if parts[0].strip() else None)
    title.append(parts[1].strip() if parts[1].strip() else None)
    date.append(parts[2].strip() if parts[2].strip() else None)
    author.append(parts[3].strip() if parts[3].strip() else None)
    text.append(parts[4].strip() if parts[4].strip() else None)

df = pd.DataFrame({'url': url, 'title': title, 'date': date, 'author': author, 'text': text})

#Modify date
df['date'] = pd.to_datetime(df['date'], format='mixed', utc=True)
df['date'] = df['date'].replace(pd.Timestamp("1970-01-01 00:59:59+00:00"), pd.NaT)
df = df.sort_values(by='date', ascending=True)
print(df['date'])
    