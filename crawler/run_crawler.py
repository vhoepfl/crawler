import logging
import handle_settings
import crawler
import os




dir = handle_settings.request_settings()
settings = handle_settings.read_settings_file(dir)
# save dir path in settings
settings['dir'] = dir
# Init logger
logging.getLogger("requests").setLevel(logging.WARNING) #Otherwise written to log
logging.basicConfig(filename=os.path.join(dir, 'console_output.log'), encoding='utf-8', level=logging.INFO)
print('\nSettings: ', settings, '\n')

starting_page = handle_settings.request_starting_page()
crawler = crawler.Crawler(settings, starting_page)
crawler.scrape()