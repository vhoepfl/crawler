import xml.etree.ElementTree as ET
import re

def add_txt_file(path): 
    with open(path, 'r') as fr: 
        fulltext = fr.read()
        url_split = re.split(r'<begin-of-url>([\w\W]*?)<end-of-url>', fulltext)
        for page in url_split: 
            page_data = page.split('<separate-parts>')
            url = page_data[0]
            title = page_data[1]
            date = page_data[2]
            author = page_data[3]
            text = page_data[4]

class XMLWriter:
    def __init__(self) -> None:

        # Create the root element
        self.root = ET.Element("TEIcorpus")
        # Create the TEI element with an attribute
        self.tei = ET.SubElement(self.root, "TEI", type="website")

    def _add_group(self, parent_element: ET.Element, group_name: str, subtype: str, ana: str) -> ET.Element:
        # Create the group element with attributes under the parent_element
        return ET.SubElement(parent_element, "group", name=group_name, subtype=subtype, ana=ana)

    def _add_text_element(self, parent_element: ET.Element, url: str, title: str, date: str, author: str, body_text: str, header_text: str = None) -> None:
        # Create the text element with attributes and body content under the parent_element
        text_elem = ET.SubElement(parent_element, "text", when=date if date else 'na', year="na", who=author if author else 'na', title=title, url=url)

        # Add header and body elements
        if header_text:
            header_elem = ET.SubElement(text_elem, "header")
            header_elem.text = header_text

        body_elem = ET.SubElement(text_elem, "body")
        body_elem.text = body_text


    def add_txt_file(self, path, group_name= None, subtype=None, ana=None):
        group_elem = self._add_group(self.root, group_name=group_name if group_name else '', \
                                     subtype=subtype if subtype else '', \
                                     ana=ana if ana else '')
        with open(path, 'r') as fr: 
            fulltext = fr.read()
            url_split = re.split(r'<begin-of-url>([\w\W]*?)<end-of-url>', fulltext)
            for page in url_split: 
                if page.strip() != '': 
                    page_data = page.split('<separate-parts>')
                    url = page_data[0].strip()
                    title = page_data[1].strip()
                    date = page_data[2].strip()
                    author = page_data[3].strip()
                    text = page_data[4].strip()
                    self._add_text_element(group_elem, url, title, date, author, text)

    def write_to_file(self, path): 
        tree = ET.ElementTree(self.root)
        ET.indent(tree, space="    ", level=0)  # Optional: to pretty print the XML with indentation
        tree.write(path, encoding="utf-8", xml_declaration=True)
        
