import logging
import os
import re
from remove_doublons import MinHashFilter

class TerminalOutput:
    def __init__(self, settings, folder, filename) -> None:
        self.dir = folder
        self.output_file_path = os.path.join(folder, filename)
        self.html_file_path = 'all_pages_html.txt'
        
        self.settings = settings

        self.filter_duplicates = False
        if settings ['file']['doublons']['remove_doublons']:
            self.filter_duplicates = True
            self.DuplicateFilter = MinHashFilter(settings['file']['doublons']['threshold_value'])

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
        
        self.write_count_html = 0
        self.write_count_scraped = 0
        self.buffer_size = 1
        self.html_buffer = [''] * self.buffer_size
        self.scraped_text_buffer = [''] * self.buffer_size


    def save_html(self, soup, url):
        """
        Writes a soup html object to a file, using the url as filename
        """
        # Place text in first free field of buffer
        text = '\n--- Separator ---\n' + url + '\n' + str(soup)
        self.html_buffer[self.write_count_html%self.buffer_size] = text

        # Write buffer to file if current field is last 
        if self.write_count_html%self.buffer_size == self.buffer_size-1: 
            with open(os.path.join(self.dir, self.html_file_path), 'a', encoding='utf-8') as fw:
                    fw.write(''.join(self.html_buffer))

        # Go to next free field of buffer
        self.write_count_html += 1
        

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
        
        total_visual_points = self.total_count + queue_len

        visual = int(50*(self.missing_title_and_date_count/total_visual_points))*'-' + \
                int(50*(self.missing_date_count/total_visual_points))*'T' + \
                int(50*(self.missing_title_count/total_visual_points))*'D' + \
                int(50*(self.low_count/total_visual_points))*'░' + \
                int(50*(self.mid_count/total_visual_points))*'▒' + \
                int(50*(self.high_count/total_visual_points))*'▓' + \
                int(50*(queue_len/total_visual_points))*'*'
        
        text =  f"Step {self.total_count}: {url}\n"
        text += f"{percentage} % of content of current page extracted\n"
        text += f"vol. {volume if volume else '-'}, {'⚠' if date_fallback_flag else ''} {date if date else '-'}, {author if author else '-'}, {title if title else '-'}"
        
        if self.total_count % self.frequency == 0: 
            self.do_print = True
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
                return False
        if self.settings['file']['word_count_limit'] != -1:
            if len(clean_text_words) < self.settings['file']['word_count_limit']:
                if self.do_print and self.verbose:
                    print(f'Checking page content - failed - lenght: {len(clean_text_words)} words')
                logging.info(f"Checking page content - failed - lenght: {len(clean_text_words)} words")
                return False
        if self.settings['file']['mean_line_lenght_limit'] != -1:
            if len(clean_text_words)/len(clean_text_lines) < self.settings['file']['mean_line_lenght_limit']:
                if self.do_print and self.verbose:
                    print(f'Checking page content - failed - mean line length: {len(clean_text_words)/len(clean_text_lines)}')
                logging.info(f"Checking page content - failed - mean line length: {len(clean_text_words)/len(clean_text_lines)}")
                return False
        if self.do_print and self.verbose:
            print('Checking page content - success')
        
        logging.info(f"Checking page content - success")
        return True


    def write_output(self, url, scraped_text, title, date, author, volume, percentage, flush=False): 
        """
        Appends the output to a file.
        Differents pages are put into a block of <begin-of-url> ...text <end-of-url>
        Anything else separated via <separate-parts>\n
        """
        # Check quality thresholds
        write_text = False
        if self.filter_duplicates: 
            if self.get_quality_rating(percentage, scraped_text) and self.DuplicateFilter.check_new_article(scraped_text):
                self.DuplicateFilter.add_article(scraped_text, url)
                write_text = True
        else: 
            if self.get_quality_rating(percentage, scraped_text): 
                write_text = True

        # Place text in current field
        if write_text: 
            text = '<begin-of-url>\n' + url + \
                    '\n<separate-parts>\n' + (title if title else '') + \
                    '\n<separate-parts>\n' + (date if date else '') + \
                    '\n<separate-parts>\n' + (author if author else '') + \
                    '\n<separate-parts>\n' + scraped_text + '\n<end-of-url>\n'
        else: 
            text = ''
        self.scraped_text_buffer[self.write_count_scraped%self.buffer_size] = text
        
        # Write buffer to file
        if self.write_count_scraped%self.buffer_size == self.buffer_size-1: 
            with open(self.output_file_path, 'a', encoding="utf-8") as fw:
                fw.write(''.join(self.scraped_text_buffer))

        # Go to next field
        self.write_count_scraped += 1
               
        # Adding linebreak to log, could be solved a lot cleaner
        logging.info(f"\n")
                
                    
               
    def flush_buffers(self): 
        with open(os.path.join(self.dir, self.html_file_path), 'a', encoding='utf-8') as fw:
                    fw.write(''.join(self.html_buffer[:self.write_count_html%self.buffer_size]))
        self.html_buffer = ['']*self.buffer_size
        
        with open(self.output_file_path, 'a', encoding="utf-8") as fw:
                fw.write(''.join(self.scraped_text_buffer[:self.write_count_scraped%self.buffer_size]))
        self.scraped_text_buffer = ['']*self.buffer_size

        


        
        