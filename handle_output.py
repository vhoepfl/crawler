import logging


class TerminalOutput:
    def __init__(self, verbose, frequency) -> None:
        self.verbose = verbose
        self.frequency = frequency
        self.print_count = 0

        self.low_count = 0
        self.mid_count = 0
        self.high_count = 0
        self.missing_title_count = 0
        self.missing_date_count = 0
        self.missing_title_and_date_count = 0
        self.total_count = 0
        
    def record_output(self, queue_len, url, scraped_text, percentage, title, date): 
        """
        Prints info for a single scraped page
        
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
        text += f"{percentage*100} % of content of current page extracted\n\n"
        text += f"{date}: {title}"
        
        if self.print_count == self.frequency: 
            if self.verbose: 
                print('\n\n' + visual + '\n' + text)
            else: 
                print('\n\n' + visual)
            self.print_count = 0

        logging.info(visual + '\n' + text)


        
        