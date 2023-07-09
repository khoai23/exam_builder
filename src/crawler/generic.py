import requests
from bs4 import BeautifulSoup

def get_parsed(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, "html.parser");
    return soup 
    
def get_text_from_url(url):
    return get_parsed(url).text