import requests
from bs4 import BeautifulSoup
import re
import handle_output
import handle_output
from time import sleep

class Crawler: 
    def __init__(self, settings, starting_url) -> None:
        self.settings = settings
        self.queue = set([starting_url])
        self.visited = set()
        self.base_url = self.get_base_url(starting_url)
        
        if self.settings['ignore_robots.txt']: 
            self.delay = 0
        else:
            self.delay = self.get_robotstxt_delay()

    def scrape(self): 
        TerminalOut = handle_output.TerminalOutput(verbose=True, frequency=1)
        
        while self.queue: 
            url, soup = self._scrape_single_page_from_queue()
            text, percentage = self._extract_text(soup)
            title, date = self._extract_metadata(soup)
            #Adding new links to queue
            self._extract_links(soup)
            TerminalOut.record_output(len(self.queue), url, text, percentage, title, date)
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
        complete_text = soup.get_text()

        #Using tags defined in settings
        if self.settings['specific_tags'][0] is not None: 
            text = soup.find_all(self.settings['specific_tags'])
            percentage = len(text) / len(complete_text)
        #Using <p> tags
        elif self.settings['only_p_text']: 
            text = soup.find_all('p')
            percentage = len(text) / len(complete_text)
        #Fallback option: Extracting anything
        else: 
            text = complete_text
            percentage = 1
        
        return text, percentage

    def _extract_metadata(self, soup): 
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

        #TODO: Implement fallback method with first datelike object
        return title, date




        

    


    def get_base_url(self, url):
        pattern = r"https?://.*\.(?:org|com|fr)"
        site = re.match(pattern, url)
        if site is None: 
            raise ValueError("Either the link is not valid or I fucked up") 
        print('base url: ', site)
        return site.group() #string from match object