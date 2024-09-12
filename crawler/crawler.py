import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from bs4 import BeautifulSoup, Tag
import re
import handle_output
import logging
import html2text


class Crawler: 
    def __init__(self, settings, starting_url) -> None:
        # Browser config
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

        # Output config
        text_output_path = 'scraped_pages_' + re.sub('(?<=_)_|(?<=^)_|_+$', '', re.sub(r'\W|https?|html', '_', starting_url[:100])) + '.txt'
        self.OutputHandler = handle_output.TerminalOutput(settings['output'], folder=settings['dir'], filename=text_output_path)

        # Crawler config
        self.settings = settings
        self.base_url = self.get_base_url(starting_url)
        self.queue = set([starting_url])
        self.visited = set()
       
        self.ignored_pages =  re.compile(re.sub(r'(/|\\)', r'\\\1', '|'.join(self.settings['general']['pages_to_be_ignored']))) \
            if self.settings['general']['pages_to_be_ignored'] else re.compile('')
        self.ignored_page_types = re.compile(r'.*\.(png|pdf|jpg)')
        self.absolute_url_pattern = re.compile(r'^(?:[a-z+]+:)?\/\/') # matches absolute urls paths as compared to relative ones

        date_pattern_str = r'(?i)\d{1,4}\D{1,3}(\d{1,2}|janvier|février|fevrier|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|décembre|decembre)\D{1,3}\d{1,4}'
        self.date_pattern = re.compile(date_pattern_str)

        volume_string = r'\b(?:[Vv]ol(?:ume)?|[Nn]um(?:éro)?|[Nn]o?|[ÉéEe]d(?:ition)?|Issue|Iss|Livraison|Livr)[\Wº°]{1,3}([IVXLC]+|\d+)'
        self.volume_pattern = re.compile(volume_string) # group 1 returns the number either in arabic or roman numerals

        # html2text config
        self.html_to_md = html2text.HTML2Text()
        self.html_to_md.ignore_links = True
        self.html_to_md.ignore_images = True
        self.html_to_md.single_line_break = False
        self.html_to_md.asterisk_emphasis = True
        self.html_to_md.ignore_emphasis = True
        self.html_to_md.body_width = 0

    def scrape(self): 
        """
        Iterates over queue, calling scraping and output functions
        """
        while self.queue:
            status, url, soup = self._scrape_single_page_from_queue()

            if status:
                # Adding new links to queue
                self._extract_links(soup)
                # Extracting data
                title, date, date_fallback_flag, author, volume = self._extract_metadata(soup)
                complete_text, text, percentage = self._extract_text(soup)
                
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

                # Evaluate and mark all elements for visibility
                self.page.evaluate("""() => {
                        document.querySelectorAll('*').forEach(el => {
                            const style = window.getComputedStyle(el);
                            const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                            if (isVisible) {
                                el.setAttribute('data-visible', 'true');
                            }
                        });
                    }""")

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
                if not re.match(self.absolute_url_pattern, link): # If absolute and not on same website: ignored
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
            # Cleanup spaces
            text = re.sub(r'[\u200B-\u200D\uFEFF]', ' ', text)# Remove zero-width-spaces
            text = re.sub(r'[^\S\r\n]*\n[^\S\r\n]*',  '\n', text) # Summarize leading spaces + linebreak + trailing spaces as single linebreak
            text = re.sub(r'\s+\Z', '', text) # Remove trailing whitespaces - leading whitespaces already removed by summarizing
            text = re.sub(r'[^\S\r\n]+', ' ', text) # Replace multiple whitespaces with a single one
            text = re.sub(r'\n{3,}', '\n\n', text) # Combine multi-linebreaks into one


            # Cleanup markdown
            text = re.sub(r'^[^\S\r\n]*\\?-\s*', '- ', text, flags=re.MULTILINE) # Escapte Aufzählungsstriche zu normalen 
            text = re.sub(r'\\\.', '.', text) # Escapte Punkte zu normalen Punkten
            text = re.sub(r'^>\s*', r'', text, flags=re.MULTILINE) # Einschub mit > entfernen
            text = re.sub(r'^([^\S\r\n]*\*[^\S\r\n]*){2,}', r'* ', text, flags=re.MULTILINE) # Mehrere Sterne zu einem 
            #text = re.sub(r'^([^\S\r\n]*\*[^\S\r\n]*)+\n', r'\n', text, flags=re.MULTILINE) # Verirrte Sterne löschen
            
            return text
        
        # Filter for specified tag
        def extract_text_recursively(root): 
            text = ""
            for child in root.children: 
                child_text = ""
                if isinstance(child, Tag):
                    for pattern in valid_patterns: 
                        if pattern['tag'] and not pattern['attrib']: # Only tag specified
                            if child.name == pattern['tag']: 
                                if child.get_text().strip():
                                    child_text = self.html_to_md.handle(str(child)) + '\n' 
                                break

                        elif pattern['tag'] and pattern['attrib']: # Tag and attrib and name specified
                            assert pattern['name'], "If an 'attrib' is used as selector, please also add a value for 'name'!"
                            name_values_for_attrib = child.get(pattern['attrib'], [])
                            if child.name == pattern['tag'] and pattern['name'] in name_values_for_attrib: 
                                if child.get_text().strip():
                                    child_text = self.html_to_md.handle(str(child)) + '\n' 
                                break

                        else: # Only attrib and name specified
                            assert pattern['name'], "If an 'attrib' is used as selector, please also add a value for 'name'!"
                            name_values_for_attrib = child.get(pattern['attrib'], [])
                            if pattern['name'] in name_values_for_attrib: 
                                if child.get_text().strip():
                                    child_text = self.html_to_md.handle(str(child)) + '\n' 
                                break

                    if child_text: 
                        text += child_text
                    else:
                        child_text = extract_text_recursively(child)
                        if child_text: 
                            text += child_text + '\n'

            return text
        
        extraction_settings = self.settings['text_extraction']
        complete_text = text_cleanup(self.html_to_md.handle(str(soup)))
        valid_patterns = extraction_settings['specific_tags']
        
        # Remove invisible elements
        for element in soup.find_all(lambda tag: not tag.has_attr('data-visible') or tag['data-visible'] != 'true'):
            element.decompose() # Removes the element from the soup

        # Extract text by tags
        if valid_patterns[0]['tag'] or valid_patterns[0]['attrib'] or valid_patterns[0]['name']: # If first tuple not empty
            text = text_cleanup(extract_text_recursively(soup))
        # Extract text by <p> (html paragraphs)
        elif extraction_settings['only_paragraphs']:
            def is_innermost(p_tag):
                return not p_tag.find('p')
            all_paragraphs = soup.find_all('p')
            innermost_paragraphs = [p for p in all_paragraphs if is_innermost(p)]
            text = text_cleanup('\n'.join([h.handle(str(p)) for p in innermost_paragraphs]))
        # Fallback option: Extract all text
        else:
            text = complete_text

        percentage = len(text) / len(complete_text) if len(complete_text) > 0 else 1
        percentage = round(percentage*100)

        return complete_text, text, percentage


    def _extract_metadata(self, soup):
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
                date_match = re.search(self.date_pattern, soup.get_text())
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
