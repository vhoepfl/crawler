import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from bs4 import BeautifulSoup
import re
import handle_output
import logging


class Crawler: 
    def __init__(self, settings, starting_url) -> None:
        self.playwright_mode = settings['general']['playwright']
        if self.playwright_mode:
            from playwright.sync_api import sync_playwright
            self.p = sync_playwright().start()
            browser = self.p.chromium.launch(headless=False, proxy={'server': 'socks5://10.64.0.1:1080'})
            self.page = browser.new_page()
        else: 
            # Add proxies for use with VPN
            proxies = {'http': 'socks5h://10.64.0.1:1080',
                    'https': 'socks5h://10.64.0.1:1080'}
            self.session = requests.Session()
            self.session.proxies.update(proxies)
        text_output_path = 'scraped_pages_' + re.sub('(?<=_)_|(?<=^)_|_+$', '', re.sub(r'\W|https?|html', '_', starting_url[:100])) + '.txt'
        self.OutputHandler = handle_output.TerminalOutput(settings['output'], folder=settings['dir'], filename=text_output_path)

        self.settings = settings
        self.base_url = self.get_base_url(starting_url)
        self.queue = set([self.base_url])
        self.visited = set()

        # TODO: Implement robots.txt handling
        self.delay = self.settings['general']['delay']

        
        self.ignored_pages = re.compile(r'.*\.(png|pdf|jpg)')
        self.match_absolute_url = re.compile(r'^(?:[a-z+]+:)?\/\/') # matches absolute urls paths as compared to relative ones

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
                    
                    title, date, date_fallback_flag, author, volume = self._extract_metadata(soup, complete_text)
                else:
                    title = None; date = None; date_fallback_flag = None; author = None; volume = None

                # Adding new links to queue
                self._extract_links(soup)
                self.OutputHandler.record_output(len(self.queue), url, text, percentage, title, date, date_fallback_flag, author, volume)
                self.OutputHandler.write_output(url, text, title, date, author, volume, percentage)
                self.OutputHandler.save_html(soup, url)

        if self.playwright_mode: 
            self.p.stop()
                

    def _scrape_single_page_from_queue(self): 
        url = self.queue.pop()
        self.visited.add(url)

        try: 
            if self.playwright_mode: 
                def scroll_down_until_no_more_pages(page):
                    # Get the initial height of the page
                    last_height = page.evaluate("document.body.scrollHeight")
                    while True:
                        # Scroll down to the bottom of the page
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        
                        # Wait for some time to let new content load
                        page.wait_for_timeout(self.delay)
                        
                        # Calculate new scroll height and compare with last scroll height
                        new_height = page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height

                self.page.goto(url)
                scroll_down_until_no_more_pages(self.page) #Makes sure the entire page was loaded
                html_content = self.page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                status = 1 # Placeholder, webpage status in playwright not directly returned
                
                     
            else: 
                r = self.session.get(url, timeout=30)
                status = 1 if r.status_code == 200 else 0
                if r.status_code != 200:
                    logging.info(f"Error when loading page {url}: {r.status_code}\n")
                    print(f"Error when loading page {url}: {r.status_code}\n")
                soup = BeautifulSoup(r.content, 'html.parser')

        except ConnectionError:
            logging.warning(f"Connection error on {url}\n")
            print(f"WARNING: Connection error on {url}")
            status = 0
            soup = None
        except Timeout:
            logging.warning(f"Request timed out on {url}\n")
            print(f"WARNING: Request timed out on {url}")
            status = 0
            soup = None
        except RequestException:
            logging.warning(f"Request exception on {url}\n")
            print(f"WARNING: Request exception on {url}")
            status = 0
            soup = None
        except Exception as e:
            logging.warning(f"Unknown exception on {url}: {e}\n")
            print(f"WARNING: Unknown exception on {url}: {e}")
            status = 0
            soup = None 

        return status, url, soup

    def _extract_links(self, soup): 
        raw_links = soup.find_all('a')
        for raw_link in raw_links: 
            link = raw_link.get('href') 
            if link is not None: 
                # Checks if link is on same site
                if re.match(self.base_url, link): 
                    if not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf
                        if link not in self.visited: # Checks if already visited
                            self.queue.add(link)
                # If link not on same site: outside -> ignore, relative link -> combine with base url
                if not re.match(self.match_absolute_url, link): # If absolute and not on same website: ignored
                    if not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf
                        full_link = self.base_url + link if len(link) > 0 and link[0] == '/' else self.base_url + '/' + link
                        if full_link not in self.visited: # Checks if already visited
                            self.queue.add(full_link)

    def _extract_text(self, soup):
        def text_cleanup(text): 
            """
            soup output should have a --separate-- separator between individual tags.
            This tag will be evaluated to check if additional spaces are needed
            """
            text = re.sub(r'(?<=\s)--separate--', '', text)
            text = re.sub(r'--separate--', ' ', text)
            text = re.sub(r'^\n+|\n+$', '', text) # Remove empty lines at the start and end
            text = re.sub(r'(?<=\n)\s*\n', '\n', text)
            return text
        
        text_settings = self.settings['text_extraction']
        #Entire website text
        complete_text = text_cleanup(soup.get_text(separator='--separate--'))
        #Using tags defined in settings
        tuples = text_settings['specific_tags']

        # Custom filter function
        def match_ids_and_classes(tag):
            for item in tuples:
                if (((tag.name == item['tag']) if item['tag'] else True) and 
                    ((tag.get('id') == item['id']) if item['id'] else True) and 
                    ((item['class'] in set(tag.get('class', []))) if item['class'] else True)): 
                    return True
            return False

        # Find all elements with specified tags
        if tuples[0]['tag'] or tuples[0]['id'] or tuples[0]['class']: #If first tuple not empty
            text = text_cleanup('--separate--'.join(tag.get_text(separator='--separate--') for tag in soup.find_all(match_ids_and_classes)))
        # Using html paragraphs
        elif text_settings['only_paragraphs']:
            all_paragraphs = soup.find_all('p')

            def is_innermost(p_tag):
                return not p_tag.find('p')

            # Filter to get only innermost <p> tags
            innermost_paragraphs = [p for p in all_paragraphs if is_innermost(p)]

            # Extract text from the innermost <p> tags
            text = text_cleanup('--separate--'.join([p.get_text(separator='--separate--') for p in innermost_paragraphs]))
        # Fallback option: Extracting anything
        else:
            text = complete_text
        percentage = len(text) / len(complete_text) if len(complete_text) > 0 else 1
        percentage = round(percentage*100)

        return complete_text, text, percentage


    def _extract_metadata(self, soup, complete_text):
        date_settings = self.settings['metadata']['date']
        title_settings = self.settings['metadata']['title']
        author_settings = self.settings['metadata']['author']
        volume_settings = self.settings['metadata']['volume']
        date_fallback = False
        title = None
        date = None
        author = None
        volume = None

        #Extracting date and title from the head of the html page
        header_title = None
        header_date = None
        header_author = None

        if title_settings['tag']:
            if title_settings['attrib'] and title_settings['name']:
                header_title = soup.find(title_settings['tag'], attrs={title_settings['attrib']: title_settings['name']})
                if header_title:
                    title = header_title.get('content')
                    if title is None: 
                        title = header_title.get_text()
            else:
                header_title = soup.find(title_settings['tag'])
                if header_title: # soup.find() returns None if not found
                    title = header_title.get_text(separator=' ')

        if date_settings['tag']:
            if date_settings['attrib'] and date_settings['name']:
                header_date = soup.find(date_settings['tag'], attrs={date_settings['attrib']: date_settings['name']})
                if header_date:
                    date = header_date.get('content')
                    if date is None: 
                        date = header_date.get_text()
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

        if author_settings['tag']:
            if author_settings['attrib'] and author_settings['name']:
                header_author = soup.find(author_settings['tag'], attrs={author_settings['attrib']: author_settings['name']})
                if header_author:
                    author = header_author.get('content')
                    if author is None: # Has no content variable, e.g. <span class="post_author_name">Les Identitaires</span>
                        author = header_author.get_text()
            else:
                header_author = soup.find(author_settings['tag'])
                if header_author:
                    author = header_author.get_text(separator=' ')        

        # Automatical extraction of volume numbers from title
        if volume_settings['extract_volume'] and title is not None:
            vol_match = re.search(self.volume_pattern, title)
            if vol_match:
                volume = vol_match.group(1)

        return title, date, date_fallback, author, volume

    def get_base_url(self, url):
        """
        Generates the base URL of the website from a complete URL
        """
        pattern = r"https?://[^/]*"
        site = re.match(pattern, url)
        if site is None:
            # Try adding 'https://'
            url_with_https = 'https://' + url
            site = re.match(pattern, url_with_https)
            if site is None:
                raise ValueError("The entered starting page is not recognized as valid link") 
        print('base url: ', site.group())
        return site.group() #string from match object
