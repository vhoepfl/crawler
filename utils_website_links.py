import re 

def base_website_from_link(link:str): 
    """
    Extracts the base website from a link, 
    e.g. https://les-identitaires.fr/tribunes/qui-[...]/ > https://les-identitaires.fr
    """

    pattern = r"https?://[^\.]\.(org|fr|de|com)"
    site = re.match(pattern, link)
    if site is None: 
        raise ValueError("No valid link found, seems to be a problem with the code, not the input") 
    return site

def 