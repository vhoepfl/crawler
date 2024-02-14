import logging
import handle_settings
import crawler 

logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)

dir = handle_settings.request_settings()
settings = handle_settings.read_settings_file(dir)
starting_page = handle_settings.request_starting_page()

crawler = crawler.Crawler(settings, starting_page)
crawler.scrape()