import logging
import os
import re
from remove_doublons import ROUGEFilter

class TerminalOutput:
    def __init__(self, settings, folder, filename) -> None:
        self.dir = folder
        self.output_file_path = os.path.join(folder, filename)
        
        self.settings = settings

        self.filter_duplicates = False
        if settings ['file']['doublons']['remove_doublons']:
            self.filter_duplicates = True
            self.DuplicateFilter = ROUGEFilter(settings['file']['doublons']['threshold_value'])

        self.verbose = settings['console']['verbose']
        self.frequency = settings['console']['print_one_per']
        # Activated at each step where output is to be printed
        self.do_print = True
        # Count values for progress visualization
        self.print_count = 0
        self.low_count = 0
        self.mid_count = 0
        self.high_count = 0
        self.missing_title_count = 0
        self.missing_date_count = 0
        self.missing_title_and_date_count = 0
        self.total_count = 0

    def save_html(self, soup, url):
        """
        Writes a soup html object to a file, using the url as filename
        """
        
        filename = 'all_pages_html.txt'

        with open(os.path.join(self.dir, filename), 'a', encoding='utf-8') as fw:
            fw.write('\n--- Separator ---\n')
            fw.write(url + '\n')
            fw.write(str(soup))
        

    def record_output(self, queue_len, url, scraped_text, percentage, title, date, date_fallback_flag, author, volume):
        """
        Prints info for the scraping process
        
        Args: 
        queue_len: Length of the queue of the crawler
        url: Scraped url
        text: Extracted text to be printed with the info
        """
        #Update visualization info: 
        if title is None and date is None: 
            self.missing_title_and_date_count += 1
        elif title is None: 
            self.missing_title_count += 1
        elif date is None: 
            self.missing_date_count += 1

        else: 
            if percentage < 0.3: 
                self.low_count += 1
            elif percentage < 0.6: 
                self.mid_count += 1
            else: 
                self.high_count += 1
        self.total_count += 1
        self.print_count += 1
        
        visual = int(self.missing_title_and_date_count/10)*'-' + \
                int(self.missing_date_count/10)*'T' + \
                int(self.missing_title_count/10)*'D' + \
                int(self.low_count/10)*'░' + \
                int(self.mid_count/10)*'▒' + \
                int(self.high_count/10)*'▓' + \
                int(queue_len/10)*'*'
        
        text =  f"Step {self.total_count}: {url}\n"
        text += f"{percentage} % of content of current page extracted\n"
        text += f"vol. {volume if volume else '-'}, {'⚠' if date_fallback_flag else ''} {date if date else '-'}, {author if author else '-'}, {title if title else '-'}"
        
        if self.print_count == self.frequency:
            self.do_print = True
            self.print_count = 0
        else:
            self.do_print = False
        
        if self.do_print:
            if self.verbose: 
                print('\n\n' + visual + '\n' + text)
            else: 
                print('\n\n' + visual)

        logging.info(visual)
        logging.info(f"Step {self.total_count}: {url}")
        logging.info(f"{percentage} % of content of current page extracted")
        logging.info(f"vol. {volume if volume else '-'}, {'⚠' if date_fallback_flag else ''} {date if date else '-'}, {author if author else '-'}, {title if title else '-'}")


    def get_quality_rating(self, percentage, scraped_text:str):
        """
        Checks if the text fulfills the quality requirements. 
        Returns: 
        0 if a check failed, 1 else
        """
        clean_text_lines = [i.strip() for i in scraped_text.split('\n') if i.strip() != '']
        clean_text_words = [i.strip() for i in scraped_text.split() if i.strip() != '']

        if self.settings['file']['percentage_limit'] != -1:
            if percentage < self.settings['file']['percentage_limit']:
                if self.do_print:
                    print(f'Checking page content - failed - percentage: {percentage}')
                logging.info(f"Checking page content - failed - percentage: {percentage} ")
                return 0
        if self.settings['file']['word_count_limit'] != -1:
            if len(clean_text_words) < self.settings['file']['word_count_limit']:
                if self.do_print and self.verbose:
                    print(f'Checking page content - failed - lenght: {len(clean_text_words)} words')
                logging.info(f"Checking page content - failed - lenght: {len(clean_text_words)} words")
                return 0
        if self.settings['file']['mean_line_lenght_limit'] != -1:
            if len(clean_text_words)/len(clean_text_lines) < self.settings['file']['mean_line_lenght_limit']:
                if self.do_print and self.verbose:
                    print(f'Checking page content - failed - mean line length: {len(clean_text_words)/len(clean_text_lines)}')
                logging.info(f"Checking page content - failed - mean line length: {len(clean_text_words)/len(clean_text_lines)}")
                return 0
        if self.do_print and self.verbose:
            print('Checking page content - success')
        
        logging.info(f"Checking page content - success")
        return 1


    def write_output(self, url, scraped_text, title, date, author, volume, percentage): 
        """
        Appends the output to a file.
        Differents pages are put into a block of <begin-of-url> ...text <end-of-url>
        Anything else separated via <separate-parts>\n
        """
        def _writer():
            with open(self.output_file_path, 'a', encoding="utf-8") as fw:
                fw.write('<begin-of-url>\n')
                fw.write(url)
                fw.write('\n<separate-parts>\n')
                fw.write(title if title else '')
                fw.write('\n<separate-parts>\n')
                fw.write(date if date else '')
                fw.write('\n<separate-parts>\n')
                fw.write(author if author else '')
                fw.write('\n<separate-parts>\n')
                fw.write(scraped_text)
                fw.write('\n<end-of-url>\n')

        if self.filter_duplicates: 
            if self.get_quality_rating(percentage, scraped_text) and self.DuplicateFilter.check_new_article(scraped_text):
                self.DuplicateFilter.add_article(scraped_text, url)
                _writer()
        else: 
            if self.get_quality_rating(percentage, scraped_text): 
                _writer()
        
        # Adding linebreak to log, could be solved a lot cleaner
        logging.info(f"\n")
                
                    
               


        
        