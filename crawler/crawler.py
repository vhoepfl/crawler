import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from bs4 import BeautifulSoup, Tag
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
        self.queue = set([starting_url])
        self.visited = set()

       
        self.ignored_pages =  re.compile(re.sub(r'(/|\\)', r'\\\1', '|'.join(self.settings['general']['pages_to_be_ignored']))) \
            if self.settings['general']['pages_to_be_ignored'] else re.compile('')
        self.ignored_page_types = re.compile(r'.*\.(png|pdf|jpg)')
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
                self.page.goto(url, timeout=60000)
                # Get the initial height of the page
                last_height = self.page.evaluate("document.body.scrollHeight")
                while True:
                    # Scroll down to the bottom of the page
                    self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    self.page.wait_for_timeout(self.settings['general']['delay'])

                    # Click all buttons on the page
                    if self.settings['general']['click_buttons']:
                        buttons = []
                        # Iterate over all selectors defined in the settings
                        for selector in self.settings['general']['click_buttons']:
                            # Fetch all elements that match the current selector and extend the button list
                            buttons.extend(self.page.query_selector_all(selector))
                        for el in buttons:
                            el.dispatch_event('click')
                        self.page.wait_for_timeout(self.settings['general']['delay'])

                    # Calculate new scroll height and compare with last scroll height
                    new_height = self.page.evaluate("document.body.scrollHeight")
                    if new_height <= last_height:
                        break
                    if new_height > last_height:
                        last_height = new_height

                self.page.goto(url, timeout=60000)

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
                    if not re.match(self.ignored_page_types, link):
                        if not self.settings['general']['pages_to_be_ignored'] or not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf or in blacklist
                            if link not in self.visited \
                                and link + '/' not in self.visited \
                                and link + '/#' not in self.visited \
                                and link + '#' not in self.visited: # Checks if already visited
                                    self.queue.add(link)
                # If link not on same site: outside -> ignore, relative link -> combine with base url
                if not re.match(self.match_absolute_url, link): # If absolute and not on same website: ignored
                    if not re.match(self.ignored_page_types, link):
                        if not self.settings['general']['pages_to_be_ignored'] or not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf or in blacklist
                            full_link = self.base_url + link if len(link) > 0 and link[0] == '/' else self.base_url + '/' + link
                            if full_link not in self.visited \
                                and full_link + '/' not in self.visited \
                                and full_link + '/#' not in self.visited \
                                and full_link + '#' not in self.visited: # Checks if already visited
                                    self.queue.add(full_link)


    def _extract_text(self, soup):
        def text_cleanup(text):
            """
            soup output should have a --separate-- separator between individual tags.
            This tag will be evaluated to check if additional spaces are needed
            """
            # Handling separators
            text = re.sub(r'(?<=\s)--separate--', '', text) # Deletes separator after newline/whitespace
            text = re.sub(r'\s*--separate--\Z', '', text) # Deletes separator at the end of the text
            text = re.sub(r'--separate--', '\n', text) # Separators in the text -> space

            # Cleanup
            text = re.sub(r'\s*\n\s*',  '\n', text) # Summarize leading spaces + linebreak + trailing spaces as single linebreak
            text = re.sub(r'^\s+', '', text) # Remove leading whitespaces
            text = re.sub(r'[^\S\n]+', ' ', text) # Replace multiple whitespaces with a single one
            text = re.sub(r'\n\n+', '\n', text) # Combine multi-linebreaks into one
            return text
        
        text_settings = self.settings['text_extraction']
        complete_text = text_cleanup(soup.get_text(separator='--separate--'))
        valid_patterns = text_settings['specific_tags']
        
        # Removing invisible elements
        for invisible_element in soup.find_all(style=lambda value: value and ('display:none' in value or 'font-size:0px' in value)):
            invisible_element.replace_with('')

        # Filter for specified tag
        def extract_text_recursively(root): 
            text = ""
            for child in root.children: 
                child_text = ""
                if isinstance(child, Tag):
                    for pattern in valid_patterns: 
                        if pattern['tag'] and not pattern['attrib']: # Only tag specified
                            if child.name == pattern['tag']: 
                                print(f'matched {child}')
                                child_text = child.get_text(separator='--separate--') + '--separate--'
                                break

                        elif pattern['tag'] and pattern['attrib']: # Tag and attrib and name specified
                            assert pattern['name'], "If an 'attrib' is used as selector, please also add a value for 'name'!"
                            name_values_for_attrib = child.get(pattern['attrib'], [])
                            if child.name == pattern['tag'] and pattern['name'] in name_values_for_attrib: 
                                print(f'matched {child}')
                                child_text = child.get_text(separator='--separate--') + '--separate--'
                                break

                        else: # Only attrib and name specified
                            assert pattern['name'], "If an 'attrib' is used as selector, please also add a value for 'name'!"
                            name_values_for_attrib = child.get(pattern['attrib'], [])
                            if pattern['name'] in name_values_for_attrib: 
                                print(f'matched {child}')
                                child_text = child.get_text(separator='--separate--') + '--separate--'
                                break

                    if child_text: 
                        print('Got child text: ', child_text, '\n\n')
                        text += child_text
                    else:
                        text += extract_text_recursively(child) + '--separate--'

            return text
  
        # Find all elements with specified tags
        if valid_patterns[0]['tag'] or valid_patterns[0]['attrib'] or valid_patterns[0]['name']: # If first tuple not empty
            text = text_cleanup(extract_text_recursively(soup))
            print(text)
        
        # Filter for <p> (html paragraphs)
        elif text_settings['only_paragraphs']:
            def is_innermost(p_tag):
                return not p_tag.find('p')
            
            all_paragraphs = soup.find_all('p')
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
        volume = None

        def check_if_match(settings):
            if settings['tag']:
                tags = soup.find_all(settings['tag'])
                for tag in tags:
                    if settings['attrib'] and settings['name']:
                        if tag.has_attr(settings['attrib']) and settings['name'] in tag.get(settings['attrib'], []):
                            return tag.get('content', '') or tag.get_text()
                    else:
                        return tag.get_text(separator=' ')
            return None

        title = check_if_match(title_settings)
        date = check_if_match(date_settings)
        author = check_if_match(author_settings)

        #Fallback method: Extract first date-like string from website text
        if not date:
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
