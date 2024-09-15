import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from bs4 import BeautifulSoup, Tag, NavigableString
import re
import handle_output
import logging
import html2text
import json
from markdownify import markdownify as md

# html2text config

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
        self.base_url = self._get_base_url(starting_url)
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
        
    def scrape(self): 
        """
        Iterates over queue, calling scraping and output functions
        """
        while self.queue:
            status, url, soup = self._scrape_single_page_from_queue()

            if status:
                self.OutputHandler.save_html(soup, url)
                # Adding new links to queue
                self._extract_links(soup)
                # Extracting metadata
                title, date, date_fallback_flag, author, volume = self._extract_metadata(soup)
                # Extracting text
                complete_text, text, percentage = self._extract_text(soup) # Modifies soup! 
                
                self.OutputHandler.record_output(len(self.queue), url, text, percentage, title, date, date_fallback_flag, author, volume)
                self.OutputHandler.write_output(url, text, title, date, author, volume, percentage)

        if self.playwright_mode: 
            self.p.stop()
                

    def _scrape_single_page_from_queue(self): 
        url = self.queue.pop()
        self.visited.add(url)

        try:
            if self.playwright_mode:
                self.page.goto(url, timeout=60000)
                
                # Scroll page
                delay_time = self.settings['general']['delay']/50
                self.page.evaluate('''
                    async (delay_time) => {
                        const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
                        for (let i = 0; i < document.body.scrollHeight; i += 100) {
                            window.scrollTo(0, i);
                            await delay(delay_time);  // Use the passed delay_time
                        }
                    }
                ''', delay_time)  
                self.page.wait_for_timeout(self.settings['general']['delay']/2)

                # Click all buttons on the page
                if self.settings['general']['click_buttons']:
                    buttons = []
                    # Iterate over all selectors defined in the settings
                    for selector in self.settings['general']['click_buttons']:
                        # Fetch all elements that match the current selector and extend the button list
                        buttons.extend(self.page.query_selector_all(selector))
                    for el in buttons:
                        el.dispatch_event('click')
                    self.page.wait_for_timeout(self.settings['general']['delay']/2)

                # Mark visible elements
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
                soup = BeautifulSoup(html_content, 'lxml')
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
        def test_variants_visited(link): 
            """
            Checks for all equivalent versions of a url if they were already visited. 
            Returns: True if already visited
            """
            variants = [link]
            if link[-2:] == '/#':
                variants.append(link[:-1])
                variants.append(link[:-2])
            elif link[-1:] == '/': 
                variants.append(link[:-1])
            else: 
                variants.append(link + '/')
                variants.append(link + '/#')

            for v in variants: 
                if v in self.visited: 
                    return True
            return False

        raw_links = soup.find_all('a')
        for raw_link in raw_links: 
            link = raw_link.get('href') 
            if link is not None: 
                # Checks if link is on same site
                if re.match(self.base_url, link):
                    if not re.match(self.ignored_page_types, link):
                        if not self.settings['general']['pages_to_be_ignored'] or not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf or in blacklist
                            if not test_variants_visited(link): # Checks if already visited
                                self.queue.add(link)
                # If link not on same site: outside -> ignore, relative link -> combine with base url
                if not re.match(self.absolute_url_pattern, link): # If absolute and not on same website: ignored
                    if not re.match(self.ignored_page_types, link):
                        if not self.settings['general']['pages_to_be_ignored'] or not re.match(self.ignored_pages, link): # Checks if is a png/jpg/pdf or in blacklist
                            full_link = self.base_url + link if len(link) > 0 and link[0] == '/' else self.base_url + '/' + link
                            if not test_variants_visited(full_link): # Checks if already visited
                                self.queue.add(full_link)


    def _extract_text(self, soup):      
        def get_check_pattern_func(valid_patterns:list): 
            """
            Returns a filter function, which matches it's tag input to the valid patterns
            Args: 
            pattern: A list of dicts, with a single tag configuration (tag, attrib, name) per dict.  
                All 2 keys have to be presents, values may be empty strings
            """
            def check_pattern_func(tag): 
                """
                Filter function, checks if input matches valid patterns. 
                """
                if tag is not None: 
                    for pattern in valid_patterns: 
                        if pattern['tag'] and not pattern['attrib']: # Only tag specified
                            if tag.name == pattern['tag']: 
                                return True
                            
                        elif pattern['tag'] and pattern['attrib']: # Tag and attrib and name specified
                            assert pattern['name'], "If an 'attrib' is used as selector, please also add a value for 'name'!"
                            name_values_for_attrib = tag.get(pattern['attrib'], [])
                            if tag.name == pattern['tag'] and pattern['name'] in name_values_for_attrib: 
                                return True
                            
                        else: # Only attrib and name specified
                            assert pattern['name'], "If an 'attrib' is used as selector, please also add a value for 'name'!"
                            name_values_for_attrib = tag.get(pattern['attrib'], [])
                            if pattern['name'] in name_values_for_attrib: 
                                return True
                return False
            
            return check_pattern_func
        
        def decompose_rec(tag, match_func, only_innermost=False):
            """
            Decomposes the bs4 soup to keeps only matched tags, but with general structure intact
            Args: 
            pattern (list of dict): HTML tag patterns saved as a dict with the keys 'tag', 'attrib' and 'name'. 
                                    Valid subsets: (tag), (attrib, name), (tag, attrib, name)
            only_innermost (bool):  If True, matches are only checked for innermost tags, content of all other tags is decomposed. 
            """
            for c in list(tag.children): 
                if isinstance(c, NavigableString): 
                    c.replace_with('')
                elif isinstance(c, Tag): 
                    if match_func(c): # c matches a pattern
                        if only_innermost: 
                            if not any(isinstance(el, Tag) for el in c.children): # is innermost
                                pass # Keep tag and children
                            else: 
                                decompose_rec(c, match_func, only_innermost=True)
                        else: 
                            pass # Keep tag and children
                    elif c.find(match_func): # descendants of c match patterns
                        decompose_rec(c, match_func)
                    else: # c and descendants don't match patterns (due to recursive nature: parents also don't match patterns)
                        c.decompose()

                else: 
                    try: 
                        c.decompose()
                    except Exception as e: 
                        print(e)

        # Remove invisible or empty (=no text content) elements
        to_decompose = []
        if soup.find_all(lambda tag: tag.has_attr('data-visible')): # If playwright was used
            for el in soup.find_all(lambda tag: (not tag.get_text(strip=True)) or not tag.has_attr('data-visible') or tag['data-visible'] != 'true'):
                to_decompose.append(el) 
        else: 
            for el in soup.find_all(True):
                style = el.get('style', '').lower()
                if (not el.get_text(strip=True)) or 'display: none' in style or 'visibility: hidden' in style or 'opacity: 0' in style:
                    to_decompose.append(el)

        for el in to_decompose:
            el.decompose() 

        complete_text = self._html_to_text(str(soup))

        extraction_settings = self.settings['text_extraction']
        valid_patterns = extraction_settings['specific_tags']

        tags_specified = False
        for el in valid_patterns: 
            if el['tag'] or el['attrib'] or el['name']: 
                tags_specified = True
                break
        # Extract text by tags if settings contain specified tags
        if tags_specified: 
            match_func = get_check_pattern_func(valid_patterns)
            decompose_rec(soup, match_func)
            text = self._html_to_text(str(soup))
        # Extract *innermost* text by <p> (html paragraphs)
        elif extraction_settings['only_paragraphs']:
            match_func = get_check_pattern_func([{'tag': 'p', 'attrib': '', 'name': ''}])
            decompose_rec(soup, match_func, only_innermost=True)
            text = self._html_to_text(str(soup))
        # Fallback option: Extract all text
        else:
            text = complete_text

        percentage = round((len(text) / len(complete_text) if len(complete_text) > 0 else 1)*100)

        return complete_text, text, percentage


    def _extract_metadata(self, soup):
        def check_if_match(settings):
            # Extraction from yoast seo script 
            if 'yoast_seo_name' in settings.keys() and settings['yoast_seo_name']: 
                tags = soup.find_all(settings['tag'])
                yoast_text = ''
                for tag in tags:
                    if settings['attrib'] and settings['name']:
                        if tag.has_attr(settings['attrib']) and settings['name'] in tag.get(settings['attrib'], []):
                            yoast_text = tag.get_text()
                            break
                    else:
                        yoast_text =  tag.get_text()
                        break

                if yoast_text: 
                    yoast_data = json.loads(yoast_text)
                    for item in yoast_data.get('@graph', []):
                        if settings['yoast_seo_name'] in item:
                            return item.get(settings['yoast_seo_name'])
            else: 
                # Robust extraction from normal html
                if settings['tag']:
                    tags = soup.find_all(settings['tag'])
                    for tag in tags:
                        if settings['attrib'] and settings['name']:
                            if tag.has_attr(settings['attrib']) and settings['name'] in tag.get(settings['attrib'], []):
                                return tag.get('content', '') or tag.get_text() or tag.get('value', '')
                        else:
                            return tag.get_text(separator=' ')
            return None

        date_settings = self.settings['metadata']['date']
        title_settings = self.settings['metadata']['title']
        author_settings = self.settings['metadata']['author']
        volume_settings = self.settings['metadata']['volume']

        title = check_if_match(title_settings)
        date = check_if_match(date_settings)
        author = check_if_match(author_settings)

        # Date: Fallback method - extract first date-like string from website text
        date_fallback = False
        if not date:
            if date_settings['use_fallback_method']:
                date_match = re.search(self.date_pattern, soup.get_text())
                if date_match:
                    date = date_match.group()
                    date_fallback = True # Flag used in output

        # Automatical extraction of volume numbers from title
        volume = None
        if volume_settings['extract_volume'] and title is not None:
            vol_match = re.search(self.volume_pattern, title)
            if vol_match:
                volume = vol_match.group(1)

        return title, date, date_fallback, author, volume


    def _get_base_url(self, url):
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


    def _html_to_text(self, html_string): 
        """
        Converts the html_string to plain text using html2text. 
        Creates a new html2text object each time to reduce the impact of a html2text bug, 
        where part of the content is accumulated at the end of the Markdown text. 
        *markdownify* would be an alternative, but html2text output is more similar to the website formatting
        """
        def text_cleanup(text):
            """
            Can be used to clean the Markdown output of html2text. 
            """
            # Cleanup spaces
            text = re.sub(r'[\u200B-\u200D\uFEFF]', ' ', text)# Remove zero-width-spaces
            text = re.sub(r'^\s+\n', '', text) # Remove spaces at start of text
            #text = re.sub(r'[^\S\r\n]*\n[^\S\r\n]*',  '\n', text) # Summarize leading spaces + linebreak + trailing spaces as single linebreak
            text = re.sub(r'\s+\Z', '', text) # Remove trailing whitespaces - leading whitespaces already removed by summarizing
            text = re.sub(r'\n\s*\n', '\n\n', text) # Combine multi-linebreaks into one

            # Cleanup markdown
            # To reformat / clean up links: (?<![!\\\s*_])\[\s*(.*?)\s*\]

            #text = re.sub(r'^[^\S\r\n]*\\?-\s*', '- ', text, flags=re.MULTILINE) # Escapte Aufzählungsstriche zu normalen 
            #text = re.sub(r'\\\.', '.', text) # Escapte Punkte zu normalen Punkten
            #text = re.sub(r'^>\s*', r'', text, flags=re.MULTILINE) # Einschub mit > entfernen
            #text = re.sub(r'^([^\S\r\n]*\*[^\S\r\n]*){2,}', r'* ', text, flags=re.MULTILINE) # Mehrere Sterne zu einem 
            #text = re.sub(r'^([^\S\r\n]*\*[^\S\r\n]*)+\n', r'\n', text, flags=re.MULTILINE) # Verirrte Sterne löschen
            
            return text
        
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.single_line_break = False
        h.asterisk_emphasis = True
        h.body_width = 0
        h.unicode_snob = True
        h.ignore_tables = True
        h.escape_snob = True
        h.dash_unordered_list = True

        return text_cleanup(h.handle(html_string))