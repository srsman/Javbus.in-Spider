# 
# Spider
# 
# Created by 吴问涵 on 7/23/16.
# 12:57
# Copyright (c) 2016 吴问涵. All rights reserved.
#

import urllib.request
import urllib.error

import subprocess
from bs4 import *
import time
import pymongo
import re

# Proxy
proxy = True
proxy_address = 'http://127.0.0.1:8118'

# Mongodb
db_username = 'wuwenhan'
db_password = '259253'
# If no mechanism is specified,
# PyMongo automatically uses MONGODB-CR when connected to a pre-3.0 version of MongoDB,
# and SCRAM-SHA-1 when connected to a recent version.
db_authentication_mechanism = 'SCRAM-SHA-1'

class Spider:

    def __init__(self):
        # Setup proxy
        if proxy:
            # Setup proxy
            enable_proxy = True
            proxy_handler = urllib.request.ProxyHandler({'https': proxy_address})
            null_proxy_handler = urllib.request.ProxyHandler({})
            if enable_proxy:
                opener = urllib.request.build_opener(proxy_handler)
            else:
                opener = urllib.request.build_opener(null_proxy_handler)
            urllib.request.install_opener(opener)
            print('Set proxy success')

        # Setup Mongodb
        self.__client = pymongo.MongoClient()
        self.__client.javbus.authenticate(db_username, db_password, mechanism=db_authentication_mechanism)

    def run(self):
        try:
            page = 75
            while page != 0:
                current_url, _ = self.__process_option(self.__option)
                request = urllib.request.Request(current_url + str(page), headers=self.__headers)
                response = urllib.request.urlopen(request)
                # print(response.read())
                soup = BeautifulSoup(response.read(), 'xml')
                # print(soup.prettify())

                movies = soup.find_all('a', class_='movie-box')
                for movie in movies:
                    # print(movie.prettify())

                    # Get detail page of current movie
                    detail_url = movie.get('href')

                    # Redirect to detail page
                    time.sleep(1)
                    new_request = urllib.request.Request(detail_url, headers=self.__headers)
                    new_response = urllib.request.urlopen(new_request)
                    new_soup = BeautifulSoup(new_response.read(), 'xml')
                    time.sleep(1)

                    raw_movie = new_soup.find('div', class_='row movie')
                    raw_text = raw_movie.prettify()
                    # print(raw_text)

                    # Get movie infos
                    id, cover, title, release_date, length, genres, stars = self.__get_infos_except_magnets(raw_movie, raw_text)
                    magnets = self.__getMagnets(detail_url)

                    self.__save_to_mongo(id, cover, title, release_date, length, genres, stars, magnets)

                next_page = soup.find('ul', class_='pagination pagination-lg')
                number_str = re.search('\d+" id="next"', str(next_page))
                if number_str:
                    page = re.search('\d+', number_str.group()).group()
                    print(page)
                else:
                    page = 0

            print('All done, enjoy :-)')

        except urllib.error.URLError as e:
            if hasattr(e, "code"):
                print(e.code)
            if hasattr(e, "reason"):
                print(e.reason)

    # Headers
    __headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:47.0) Gecko/20100101 Firefox/47.0'
    }

    def __get_infos_except_magnets(self, raw_movie, raw_text):

        id = raw_movie.find('span', style='color:#CC0000;').string
        # print(id)

        temp = raw_movie.find('a', class_='bigImage')

        cover = temp.img.get('src')
        # print(cover)

        title = temp.img.get('title')
        # print(title)

        release_date = re.search(r'\d{2,4}-\d{1,2}-\d{1,2}', raw_text).group(0)
        # print(release_date)

        length = re.search(r'\d{0,5}分鐘', raw_text).group(0)
        # print(length)

        stars = set()
        for star in raw_movie.find_all('div', class_='star-name'):
            stars.add(star.a.string)
        # print(stars)

        genres = set()
        for genre in raw_movie.find_all('span', class_='genre'):
            genres.add(genre.a.string)
        genres = (genres - self.__trash_word) - stars
        # print(genres)

        return id, cover, title, release_date, length, genres, stars

    def __getMagnets(self, url):
        cmd = 'phantomjs ./phantomjs.js "{}"'.format(url)
        stdout, stderr = subprocess.Popen(cmd,
                                          shell=True,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          ).communicate()

        # temp_str = re.search('magnet.*', stdout.decode())
        array = stdout.decode().split('\n')
        temp = filter(self.__check, array)
        magnets = list(temp)
        return magnets

    @staticmethod
    def __check(string):
        if len(string) < 6:
            return False
        if string[0:6] == 'magnet':
            return True
        else:
            return False

    def __save_to_mongo(self, id, cover, title, release_date, length, genres, stars, magnets):

        movie = {
            'id': id,
            'cover': cover,
            'title': title,
            'release_date': release_date,
            'length': length,
            'genres': list(genres),
            'stars': list(stars),
            'magnets': magnets
        }

        _, javbus = self.__process_option(self.__option)

        javbus.insert_one(movie)

    # censored, uncensored, EU (Europe & US), HD, subtitles
    __option = 'censored'

    def set_option(self, option):
        if option not in {'censored', 'uncensored', 'EU', 'Europe & US', 'HD', 'subtitles'}:
            print('Invalid option!')
            print("The only valid option is {'censored', 'uncensored', 'EU', 'Europe & US', 'HD', 'subtitles'}")
        else:
            self.__option = option
            print('Set option success')

    # URLs
    __censored_url = 'https://www.javbus.in/page/'
    __uncensored_url = 'https://www.javbus.in/uncensored/page/'
    __EU_url = 'https://www.javbus.org/page/'
    __HD_url = 'https://www.javbus.com/genre/hd/page/'
    __subtitles_url = 'https://www.javbus.com/genre/sub/page/'

    def __process_option(self, option):
        # censored, uncensored, EU (Europe & US), HD, subtitles
        if option == 'censored':
            return self.__censored_url, self.__client.javbus.censored
        elif option == 'uncensored':
            return self.__uncensored_url, self.__client.javbus.uncensored
        elif option == 'EU' or option == 'Europe & US':
            return self.__EU_url, self.__client.javbus.EU
        elif option == 'HD':
            return self.__HD_url, self.__client.javbus.HD
        elif option == 'subtitles':
            return self.__subtitles_url, self.__client.javbus.subtitles

    # Trash words
    __trash_word = {'淫滿直播間', '騷浪色主播', 'D奶慾女', '絕對射出', '現場噴射中', '真人裸聊'}

    def add_trash_word(self, word):
        self.__trash_word.add(word)

    def remove_trash_word(self, word):
        if word not in self.__trash_word:
            self.__trash_word = self.__trash_word - set(word)