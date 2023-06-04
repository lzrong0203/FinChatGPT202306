import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time


class PTTScraper:
    base_url = "https://www.ptt.cc"

    def __init__(self):
        self.base_url = PTTScraper.base_url
        self.url = self.base_url + "/bbs/Stock/index.html"

    def get_post_content(self, post_url):
        soup = PTTScraper.get_soup(self.base_url + post_url)
        content = soup.find(id='main-content').text

        # 抓取推文
        pushes = soup.find_all('div', class_='push')

        with ThreadPoolExecutor() as executor:
            push_list = list(executor.map(self.get_push, pushes))

        return content, push_list

    def get_push(self, push):
        try:
            if push.find('span', class_='push-tag') is None:
                return dict()
            push_tag = push.find('span', class_='push-tag').text.strip()
            push_userid = push.find('span', class_='push-userid').text.strip()
            push_content = push.find('span', class_='push-content').text.strip().lstrip(":")
            push_ipdatetime = push.find('span', class_='push-ipdatetime').text.strip()
            push_dict = {
                "Tag": push_tag,
                "Userid": push_userid,
                "Content": push_content,
                "Ipdatetime": push_ipdatetime
            }
        except Exception as e:
            print(e)
        return push_dict

    @staticmethod
    def get_soup(url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/58.0.3029.110 Safari/537.3", }
        response = requests.get(url, headers=headers)
        return BeautifulSoup(response.text, 'html.parser')

    def fetch_post(self, url):
        soup = PTTScraper.get_soup(self.base_url + url)

        # Extract post information
        content = soup.find(id='main-content').text
        content = content.split('※ 發信站')[0]
        author = soup.find(class_='article-meta-value').text
        title = soup.find_all(class_='article-meta-value')[-2].text
        date_str = soup.find_all(class_='article-meta-value')[-1].text
        date = datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')

        # Extract comments
        pushes = soup.find_all('div', class_='push')

        with ThreadPoolExecutor() as executor:
            push_list = list(executor.map(self.get_push, pushes))
        #
        # comments = []
        # for div in soup.find_all('div', class_='push'):
        #     if div.find('span', 'push-tag') is None:
        #         continue
        #     push_tag = div.find('span', 'push-tag').text.strip()
        #     push_userid = div.find('span', 'push-userid').text.strip()
        #     push_content = div.find('span', 'push-content').text.strip()
        #     comments.append({'tag': push_tag, 'userid': push_userid, 'content': push_content})

        return {'Title': title, 'Author': author, 'Date': date, 'Content': content,
                'Link': url, 'Pushes': push_list}

    def get_data_current_page(self, soup=None, until_date=datetime.now(), *,
                              max_posts=100, links_num=0):
        reach = False
        if soup is None:
            soup = PTTScraper.get_soup(self.url)
        links = []
        for entry in reversed(soup.select('.r-ent')):
            try:
                if entry.find("div", "title").a is None:
                    continue
                # title = entry.select('.title')[0].text.strip()
                # author = entry.select('.author')[0].text.strip()
                date = entry.select('.date')[0].text.strip()
                links.append(entry.select('.title a')[0]['href'])
                # content, pushes = self.get_post_content(link)
                # data.append({
                #     "Title": title,
                #     "Author": author,
                #     "Date": date,
                #     "Link": link,
                #     "Content": content,
                #     "Pushes": pushes
                # })
                until_date = until_date.replace(hour=0, minute=0, second=0, microsecond=0)
                post_date = datetime.strptime(date, '%m/%d').replace(year=until_date.year)
                print(len(links))
                if len(links) + links_num >= max_posts or post_date < until_date:
                    reach = True
                    break
            except Exception as e:
                print(e)
        print(post_date)
        with ThreadPoolExecutor() as executor:
            data = list(executor.map(self.fetch_post, links))
        return data, reach, len(links)

    def get_data_until(self, until_date, *, max_posts=100):
        data = []
        date = datetime.strptime(until_date, '%m/%d').replace(year=datetime.now().year)
        links_num = 0
        while True:
            soup = PTTScraper.get_soup(self.url)
            data_curr, date_end, num = self.get_data_current_page(soup, date,
                                                                  max_posts=max_posts, links_num=links_num)
            data.extend(data_curr)

            if date_end:
                return data
            links_num += num

            # 找到上一頁的連結
            prev_link = soup.find('a', string='‹ 上頁')['href']
            self.url = self.base_url + prev_link
        return data


# 使用方式
if __name__ == "__main__":
    scraper = PTTScraper()
    begin = time.time()
    data = scraper.get_data_until("6/2", max_posts=10)
    end = time.time()
    print(end - begin)
    df = pd.DataFrame(data)
    print(df)
    print(pd.DataFrame(df.Pushes[1]))

