import requests
from bs4 import BeautifulSoup
import re

class Crawler: 
    def __init__(self, settings, starting_url) -> None:
        self.settings = settings
        self.queue = set([starting_url])
        self.visited = set()
        self.base_url = self.get_base_url(starting_url)
        
        if self.settings['ignore_robots_txt']: 
            self.delay = 0.1
        else:
            self.delay = self.get_robotstxt_delay()

    def scrape(): 
        pass

    def _scrape_single_page(self): 
        #updating queues
        url = self.queue.pop()
        self.visited.add(url)

        r = requests.get(url)
        return BeautifulSoup(r.content, 'html.parser')



    def _extract_links(self): 
        raw_links = self.soup.find_all('a')

        for raw_link in raw_links: 
            link = raw_link.get('href') 
            #Checks if link is relative / on same site
            if re.match(self.base_url, link): 
                self.queue.add(link)

    def _extract_text(self): 
        pass

    def _extract_metadata(): 
        try


    def get_robotstxt_delay(self): 
        #TODO: Implement robots txt check
        return 0.1

    def get_base_url(self, url):
        pattern = r"https?://[^\.]\.(org|fr|de|com)"
        site = re.match(pattern, url)
        if site is None: 
            raise ValueError("Either the link is not valid or I fucked up") 
        print(site)
        return site