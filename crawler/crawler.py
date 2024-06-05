import requests
from bs4 import BeautifulSoup
import re
import handle_output
from time import sleep

class Crawler: 
    def __init__(self, settings, starting_url) -> None:
        #proxies = {'http': 'http://' +'192.240.46.123:80',
        #           'https': 'https://' +'192.240.46.123:80'}
        self.session = requests.Session()
        #self.session.proxies.update(proxies)

        self.OutputHandler = handle_output.TerminalOutput(settings['output'], folder=settings['dir'], filename='scraped_pages.txt')

        self.settings = settings
        self.queue = set([starting_url])
        self.visited = set()

        # TODO: Implement robots.txt handling
        self.delay = self.settings['general']['delay']

        self.base_url = self.get_base_url(starting_url)
        self.ignored_pages = re.compile(r'.*\.(png|pdf|jpg)')
        self.local_links = re.compile(r'^\/[^\/]+$')

        datetime_string = r'(?i)\d{1,4}\D{1,3}(\d{1,2}|janvier|février|fevrier|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|décembre|decembre)\D{1,3}\d{1,4}'
        self.date_pattern = re.compile(datetime_string)

        volume_string = r'\b(?:[Vv]ol(?:ume)?|[Nn]um(?:éro)?|[Nn]o?|[ÉéEe]d(?:ition)?|Issue|Iss|Livraison|Livr)[\Wº°]{1,3}([IVXLC]+|\d+)'
        self.volume_pattern = re.compile(volume_string) # group 1 returns the number either in arabic or roman numerals

    def scrape(self): 
        """
        Iterates over queue, calling scraping and output functions
        """
        while self.queue: 
            status, url, soup = self._scrape_single_page_from_queue()

            if status:
                # Extracting data
                complete_text, text, percentage = self._extract_text(soup)
                if percentage != 0:
                    title, date, date_fallback_flag, volume = self._extract_metadata(soup, complete_text)
                else:
                    title = None; date = None; date_fallback_flag = None; volume = None

                # Adding new links to queue
                self._extract_links(soup)
                self.OutputHandler.record_output(len(self.queue), url, text, percentage, title, date, date_fallback_flag, volume)
                self.OutputHandler.write_output(url, text, title, date, volume, percentage)
                self.OutputHandler.save_html(soup, url)
                sleep(self.delay)

    def _scrape_single_page_from_queue(self): 
        url = self.queue.pop()
        self.visited.add(url)

        r = self.session.get(url)
        status = 1 if r.status_code == 200 else 0
        print('status', status, url)
        return status, url, BeautifulSoup(r.content, 'html.parser')

    def _extract_links(self, soup): 
        raw_links = soup.find_all('a')
        for raw_link in raw_links: 
            link = raw_link.get('href') 
            if link is not None: 
                # Checks if link is relative / on same site
                if re.match(self.base_url, link): 
                    if not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf
                        if link not in self.visited: # Checks if already visited
                            self.queue.add(link)
                # Checks if link is a weird local link
                elif re.match(self.local_links, link):
                    if not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf
                        # Combine local link with base url to get a full one
                        full_link = self.base_url + link if link[0] == '/' else self.base_url + '/' + link
                        if full_link not in self.visited: # Checks if already visited
                            self.queue.add(full_link)

    def _extract_text(self, soup):
        text_settings = self.settings['text_extraction']
        #Entire website text
        complete_text = soup.get_text(separator='\n')
        #Using tags defined in settings
        tags = [] if text_settings['specific_tags']['tag'] is None else \
            [t.strip() for t in text_settings['specific_tags']['tag'].split(',')]
        classes = [] if text_settings['specific_tags']['class'] is None else \
            [c.strip() for c in text_settings['specific_tags']['class'].split(',')]
        ids = [] if text_settings['specific_tags']['id'] is None else \
            [i.strip() for i in text_settings['specific_tags']['id'].split(',')]
        

        # Custom filter function
        def match_ids_and_classes(tag):
            return (tag.name in tags) or (tag.get('id') in ids) or (bool(set(tag.get('class', [])).intersection(classes)))

        # Find all elements with specified tags
        if tags or classes or ids:
            text = '\n'.join(tag.get_text(separator='\n') for tag in soup.find_all(match_ids_and_classes))
        # Using html paragraphs
        elif text_settings['only_paragraphs']:
            all_paragraphs = soup.find_all('p')

            def is_innermost(p_tag):
                return not p_tag.find('p')

            # Filter to get only innermost <p> tags
            innermost_paragraphs = [p for p in all_paragraphs if is_innermost(p)]

            # Extract text from the innermost <p> tags
            text = '\n'.join([p.get_text(separator='\n') for p in innermost_paragraphs])
        # Fallback option: Extracting anything
        else:
            text = complete_text
        percentage = len(text) / len(complete_text) if len(complete_text) > 0 else 1
        percentage = round(percentage*100)
        return complete_text, text, percentage


    def _extract_metadata(self, soup, complete_text):
        date_settings = self.settings['metadata']['date']
        title_settings = self.settings['metadata']['title']
        volume_settings = self.settings['metadata']['volume']

        date_fallback = False
        title = None
        date = None
        volume = None

        #Extracting date and title from the head of the html page
        header_title = None
        header_date = None
        print(title_settings)
        if title_settings['tag']:
            if title_settings['attrib'] and title_settings['name']:
                header_title = soup.find(title_settings['tag'], attrs={title_settings['attrib']: title_settings['name']})
                if header_title:
                    title = header_title.get('content')
            else:
                header_title = soup.find(title_settings['tag'])
                if header_title: # soup.find() returns None if not found
                    title = header_title.get_text(separator=' ')

        if date_settings['tag']:
            if date_settings['attrib'] and date_settings['name']:
                header_date = soup.find(date_settings['tag'], attrs={date_settings['attrib']: date_settings['name']})
                if header_date:
                    title = header_title.get('content')
            else:
                header_date = soup.find(date_settings['tag'])
                if header_date:
                    date = header_date.get_text(separator=' ')

        #Fallback method: Extract first date-like string from website text
        if not header_date:
            if date_settings['use_fallback_method']:
                date_match = re.search(self.date_pattern, complete_text)
                if date_match:
                    date = date_match.group()
                    date_fallback = True # Flag used in output

        # Automatical extraction of volume numbers from title
        if volume_settings['extract_volume'] and title is not None:
            vol_match = re.search(self.volume_pattern, title)
            if vol_match:
                volume = vol_match.group(1)

        return title, date, date_fallback, volume

    def get_base_url(self, url):
        """
        Generates the base URL of the website from a complete URL
        """
        pattern = r"https?://[^/]*"
        site = re.match(pattern, url)
        if site is None:
            raise ValueError("The entered starting page is not recognized as valid link") 
        print('base url: ', site)
        return site.group() #string from match object