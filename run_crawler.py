import logging
import handle_settings
import crawler 

logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.INFO) #TODO write to folder
logging.getLogger("requests").setLevel(logging.WARNING) #Otherwise written to log

dir = handle_settings.request_settings()
settings = handle_settings.read_settings_file(dir)
print(settings)
starting_page = handle_settings.request_starting_page()

crawler = crawler.Crawler(settings, starting_page)
crawler.scrape()