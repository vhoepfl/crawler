import logging
from logging import FileHandler
from logging.handlers import MemoryHandler
import threading
import handle_settings
import crawler
import os
import time
import re


    
dir = handle_settings.request_settings()
settings = handle_settings.read_settings_file(dir)
# save dir path in settings
settings['dir'] = dir

# Init logger
# Set up file handler
log_file = os.path.join(dir, 'console_output.log')
file_handler = FileHandler(log_file, encoding='utf-8')
# Set up memory handler that buffers 10 log records before writing to the file
memory_handler = MemoryHandler(capacity=50, flushLevel=logging.ERROR, target=file_handler)
# Configure logging to use memory handler
logging.basicConfig(handlers=[memory_handler], level=logging.INFO)
# Prevent verbose logging from requests
logging.getLogger("requests").setLevel(logging.WARNING)
print('\nSettings: ', settings, '\n')

# Init crawler
starting_page = handle_settings.request_starting_page()
crawler = crawler.Crawler(settings, starting_page)

# Start thread to update *pages_to_be_ignored*
def keep_settings_updated(): 
    while True: 
        time.sleep(60)
        actualized_settings = handle_settings.read_settings_file(dir)
        if actualized_settings['general']['pages_to_be_ignored']: 
            old_ignored_pages = crawler.ignored_pages
            new_ignored_pages = re.sub(r'(/|\\)', r'\\\1', '|'.join(actualized_settings['general']['pages_to_be_ignored']))
            if new_ignored_pages != old_ignored_pages: 
                crawler.ignored_pages = new_ignored_pages
                logging.warning(f'Using new settings: Ignoring "{new_ignored_pages}" instead of "{old_ignored_pages}"')
                print(f'Using new settings: Ignoring "{new_ignored_pages}" instead of "{old_ignored_pages}"')
                # Delete all unwanted elements from queue
                del_count = 0
                for el in list(crawler.queue): 
                    if re.search(new_ignored_pages, el): 
                        crawler.queue.discard(el)
                        del_count += 1
                logging.warning(f'Deleted {del_count} elements from queue\n')
                print(f'Deleted {del_count} elements from queue')

reload_thread = threading.Thread(target=keep_settings_updated)
reload_thread.daemon = True
reload_thread.start()

# Start crawler
crawler.scrape()


