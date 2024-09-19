import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from bs4 import BeautifulSoup, Tag, NavigableString
import re
import handle_output
import logging
import html2text
import json


class Crawler: 
    def __init__(self, settings, starting_url) -> None:
        # Browser config
        self.playwright_mode = settings['general']['playwright']
        if self.playwright_mode:
            from playwright.sync_api import sync_playwright
            self.p = sync_playwright().start()
            self.browser = self.p.chromium.launch(headless=True, proxy={'server': 'socks5://10.64.0.1:1080'})
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
        self.base_url, self.base_url_pattern = self._get_base_url(starting_url)
        self.queue = set([starting_url])
        self.visited = set()
       
        self.ignored_pages =  re.sub(r'(/|\\)', r'\\\1', '|'.join(self.settings['general']['pages_to_be_ignored'])) \
            if self.settings['general']['pages_to_be_ignored'] else ''
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
        browser_visit_count = 0
        if self.playwright_mode: 
            context = self.browser.new_context()
            self.page = context.new_page()

        while self.queue:
            # re-init web browser each 100 visited pages (deletes cookies etc.)
            if browser_visit_count == 50: 
                if self.playwright_mode: 
                    context.close()
                    context = self.browser.new_context()
                    self.page = context.new_page()
                else: 
                    proxies = {'http': 'socks5h://10.64.0.1:1080',
                    'https': 'socks5h://10.64.0.1:1080'}
                    self.session = requests.Session()
                    self.session.proxies.update(proxies)
                browser_visit_count = 0
                print('INFO: Restarted browser session.\n')
            browser_visit_count += 1
            
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

        # Write all buffers to files
        self.OutputHandler.flush_buffers()
        if self.playwright_mode: 
            self.p.stop()
                

    def _scrape_single_page_from_queue(self): 
        url = self.queue.pop()
        self.visited.add(url)
        try:
            if self.playwright_mode:
                self.page.goto(url, timeout=240000)
                
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
                if re.match(self.base_url_pattern, link):
                    if not re.match(self.ignored_page_types, link):
                        if not self.ignored_pages or re.search(self.ignored_pages, link) is None: # Checks if is a png/jpg/pdf or in blacklist
                            if not test_variants_visited(link): # Checks if already visited
                                self.queue.add(link)
                # If link not on same site: outside -> ignore, relative link -> combine with base url
                if not re.match(self.absolute_url_pattern, link): # If absolute and not on same website: ignored
                    full_link = self.base_url + link if len(link) > 0 and link[0] == '/' else self.base_url + '/' + link
                    if not re.match(self.ignored_page_types, link):
                        if not self.ignored_pages or not re.search(self.ignored_pages, link): # Checks if is a png/jpg/pdf or in blacklist
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
                            if tag.name == pattern['tag']: 
                                all_names_match = True
                                for name in pattern['name'].split():
                                    if name not in name_values_for_attrib: 
                                        all_names_match = False
                                if all_names_match:
                                    return True
                        else: # Only attrib and name specified
                            assert pattern['name'], "If an 'attrib' is used as selector, please also add a value for 'name'!"
                            name_values_for_attrib = tag.get(pattern['attrib'], [])
                            all_names_match = True
                            for name in pattern['name'].split():
                                if name not in name_values_for_attrib: 
                                    all_names_match = False
                            if all_names_match:
                                return True
                return False
            
            return check_pattern_func
        
        def decompose_rec(tag, match_func, del_matches=False):
            """
            Decomposes the bs4 soup: \n
            (del_matches = False)   Keep only matched tags, but with general structure intact \n
            (del_matches = True)    Delete all matched tags
            Args: 
            match func: A function checking whether a tag has one of the selected patterns - returns True or False
            del_matches: If True, all matching tags are deleted. If False, all matching tags are kept, any other deleted. 
            """
            for c in list(tag.children): 
                if isinstance(c, NavigableString): 
                    c.replace_with('')
                elif isinstance(c, Tag): 
                    # Deleting matches from tree
                    if del_matches: 
                        if match_func(c): 
                            c.decompose()
                        elif c.find(match_func): 
                            decompose_rec(c, match_func, del_matches)
                    # Keep only matches in tree
                    else: 
                        if match_func(c): # c matches a pattern
                            pass # Keep tag and children
                        elif c.find(match_func): # descendants of c match patterns
                            decompose_rec(c, match_func, del_matches)
                        else: # c and descendants don't match patterns (due to recursive nature: parents also don't match patterns)
                            c.decompose()

                else: 
                    try: 
                        c.decompose()
                    except Exception as e: 
                        print(e)
            
            if not tag.get_text(strip=True): # (This should not delete <br> as those are inline and thus protected where matched)
                tag.clear() # Keeps root intact to avoid NoneType errors

        # Remove invisible or empty (=no text content) elements
        to_decompose = set()
        if soup.find(lambda tag: tag.has_attr('data-visible')): # If playwright was used
            for el in soup.find_all(lambda tag: not tag.has_attr('data-visible') or tag['data-visible'] != 'true'):
                to_decompose.add(el) 

        for el in soup.find_all(True):
            style = el.get('style', '').lower()
            if 'display: none' in style or 'visibility: hidden' in style or 'opacity: 0' in style:
                to_decompose.add(el)

        for el in to_decompose:
            el.decompose() 


        complete_text = self._html_to_text(soup)
        extraction_settings = self.settings['text_extraction']
        patterns_include = extraction_settings['specific_tags_include']
        patterns_exclude = extraction_settings['specific_tags_exclude']

        include_tags_specified = False
        exclude_tags_specified = False
        for el in patterns_include: 
            if el['tag'] or el['attrib'] or el['name']: 
                include_tags_specified = True
                break
        for el in patterns_exclude: 
            if el['tag'] or el['attrib'] or el['name']: 
                exclude_tags_specified = True
                break
        tree_pruned = False
        # Extract text by tags if settings contain specified tags
        if include_tags_specified: 
            include_match_func = get_check_pattern_func(patterns_include)
            decompose_rec(soup, include_match_func)
            tree_pruned = True
        if exclude_tags_specified: 
            exclude_match_func = get_check_pattern_func(patterns_exclude)
            decompose_rec(soup, exclude_match_func, del_matches=True)
            tree_pruned = True
        # Extract text by <p> (html paragraphs)
        if extraction_settings['only_paragraphs']:
            include_match_func = get_check_pattern_func([{'tag': 'p', 'attrib': '', 'name': ''}])
            decompose_rec(soup, include_match_func)
            tree_pruned = True
        # Extract text by paragraphs and headers
        elif extraction_settings['only_paragraphs_and_headers']:
            include_match_func = get_check_pattern_func([{'tag': 'p', 'attrib': '', 'name': ''}, \
                                                {'tag': 'h1', 'attrib': '', 'name': ''}, \
                                                {'tag': 'h2', 'attrib': '', 'name': ''}, \
                                                {'tag': 'h3', 'attrib': '', 'name': ''}, \
                                                {'tag': 'h4', 'attrib': '', 'name': ''}, \
                                                {'tag': 'h5', 'attrib': '', 'name': ''}, \
                                                {'tag': 'h6', 'attrib': '', 'name': ''}])
            decompose_rec(soup, include_match_func)
            tree_pruned = True
        if tree_pruned: 
            text = self._html_to_text(soup)
        else: # Fallback option: Extract all text
            text = complete_text
        percentage = round((len(text) / len(complete_text) if len(complete_text) > 0 else 1)*100)

        return complete_text, text, percentage


    def _extract_metadata(self, soup):

        def check_if_match(settings):

            def find_in_json_rec(d, target_key): 
                if isinstance(d, dict):
                    for key, value in d.items():
                        if key == target_key:
                            return value
                        elif isinstance(value, dict):
                            result = find_in_json_rec(value, target_key)
                            if result:
                                return result
                        elif isinstance(value, list):
                            for item in value:
                                result = find_in_json_rec(item, target_key)
                                if result:
                                    return result
                return None
            
            # Extraction from yoast seo script 
            if 'json_pattern' in settings.keys() and settings['json_pattern']: 
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
                    return find_in_json_rec(yoast_data, settings['json_pattern'])
            else: 
                # Robust extraction from normal html
                if settings['tag']:
                    tags = soup.find_all(settings['tag'])
                    for tag in tags:
                        if settings['attrib'] and settings['name']:
                            if tag.has_attr(settings['attrib']) and settings['name'] in tag.get(settings['attrib'], []):
                                return tag.get('content', '') or tag.get_text() or tag.get('value', '')
                        elif settings['attrib']: 
                            return tag.get(settings['attrib'])
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
        Generates the base URL pattern of the website from a complete URL
        """
        pattern = r"https?://[^/]*"
        site = re.match(pattern, url)
        if site is None:
            # Try adding 'https://'
            url_with_https = 'https://' + url
            site = re.match(pattern, url_with_https)
            if site is None:
                raise ValueError("The entered starting page is not recognized as valid link") 
        raw_base_url = site.group()
        part_url = re.match(r'https?://?([^[^/]+)', raw_base_url).group(1)
        full_pattern = r'(https?://)?' + re.escape(part_url)
        print('base url pattern: ', full_pattern)

        return raw_base_url, full_pattern # pattern to match website


    def _html_to_text(self, soup): 
        """
        Converts the soup to plain text using html2text. 
        Creates a new html2text object each time to reduce the impact of a html2text bug, 
        where part of the content is accumulated at the end of the Markdown text. 
        *markdownify* would be an alternative, but html2text output is more similar to the website formatting
        """
        def text_cleanup(text):
            """
            Can be used to clean the Markdown output of html2text. 
            """
            # Cleanup spaces
            text = re.sub(r'---LINE_BREAK_PLACEHOLDER---', '\n', text)
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

        return text_cleanup(h.handle(str(soup)))