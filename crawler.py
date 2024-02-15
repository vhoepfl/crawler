import requests
from bs4 import BeautifulSoup
import re
import handle_output
import handle_output
from time import sleep

class Crawler: 
    def __init__(self, settings, starting_url) -> None:
        self.header_date_exists = False #If a date is found in the header, the fallback date search is deactivated
        self.settings = settings
        self.queue = set([starting_url])
        self.visited = set()
        self.base_url = self.get_base_url(starting_url)
        
        if self.settings['general']['ignore_robots.txt']: 
            self.delay = 0
        else:
            self.delay = self.get_robotstxt_delay()

        datetime_string = '(?i)\d{1,4}\D{1,3}(\d{1,2}|janvier|février|fevrier|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|décembre|decembre)\D{1,3}\d{1,4}'
        self.date_pattern = re.compile(datetime_string)

    def scrape(self): 
        TerminalOut = handle_output.TerminalOutput(verbose=True, frequency=1)
        
        while self.queue: 
            url, soup = self._scrape_single_page_from_queue()
            complete_text, text, percentage = self._extract_text(soup)
            title, date, flag_fallback = self._extract_metadata(soup, complete_text)
            #Adding new links to queue
            self._extract_links(soup)
            TerminalOut.record_output(len(self.queue), url, text, percentage, title, date, flag_fallback)
            sleep(self.delay)

    def _scrape_single_page_from_queue(self): 
        #updating queues
        url = self.queue.pop()
        self.visited.add(url)

        r = requests.get(url)
        return url, BeautifulSoup(r.content, 'html.parser')

    def _extract_links(self, soup): 
        raw_links = soup.find_all('a')
        for raw_link in raw_links: 
            link = raw_link.get('href') 
            if link is not None: 
                #Checks if link is relative / on same site
                if re.match(self.base_url, link):
                    if link not in self.visited: 
                        self.queue.add(link)

    def _extract_text(self, soup): 
        #Entire website text
        complete_text = soup.get_text(separator='\n')

        #Using tags defined in 
        specific_tags = self.settings['text_extraction']['specific_tags']
        if specific_tags[0] is not None: 
            text = '\n'.join(tag.get_text() for tag in soup.find_all(specific_tags))
            percentage = len(text) / len(complete_text) if len(complete_text) > 0 else 1
        #Using <p> tags
        elif self.settings['text_extraction']['only_p_text']: 
            text = '\n'.join(tag.get_text() for tag in soup.find_all('p'))
            percentage = len(text) / len(complete_text) if len(complete_text) > 0 else 1
        
        #Fallback option: Extracting anything
        else: 
            text = complete_text
            percentage = 1
        
        return complete_text, text, percentage

    def _extract_metadata(self, soup, complete_text): 
        flag_fallback = False
        #Returns None if not found in header
        title = None
        date = None
        #Extracting date and title from the head of the html page
        header_title = soup.find('meta', property='og:title')
        header_date = soup.find('meta', property="article:published_time")
        
        if header_title is not None: #soup.find() returns None if not found
            title = header_title.get('content')
        if header_date is not None: 
            date = header_date.get('content')
            self.header_date_exists = True #Deactivate fallback method

        #Fallback method: Extract first date-like string from website text
        if not self.header_date_exists: 
            date_match = re.search(self.date_pattern, complete_text)
            if date_match:
                date = date_match.group()
                flag_fallback = True     
        #search in whole text, not only the extracted one / <p> one 
        return title, date, flag_fallback


    def get_base_url(self, url):
        pattern = r"https?://[^/]*"
        site = re.match(pattern, url)
        if site is None: 
            raise ValueError("The entered starting page is not recognized as valid link") 
        print('base url: ', site)
        return site.group() #string from match object