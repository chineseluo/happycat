import requests
from bs4 import BeautifulSoup

url = "https://passport.jd.com/new/login.aspx"
page = requests.session().get(url)
if __name__ == '__main__':
    soup = BeautifulSoup(page.text, "html.parser")
    input_list = soup.select('.form input')
    print(input_list)
