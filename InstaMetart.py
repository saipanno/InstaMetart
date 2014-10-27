#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) Ruoyan Wong
#
# InstaMetart - main.py
#



import os
import sys
import hashlib
import subprocess
import ConfigParser
from re import search
from urllib2 import urlopen
from HTMLParser import HTMLParser
from multiprocessing import Pool


def logging(level, text):

    if level == 'info':
        print text

def running_command(command):
    try:
        do = subprocess.call('%s >> /dev/null 2>&1' % command, shell=True)
    except Exception:
        pass

class IndexPagesParser(HTMLParser):

    def __init__(self):

        HTMLParser.__init__(self)

        self.data = list()
        self.recording = False


    def handle_starttag(self, tag, attributes):
        
        if tag == 'div': 
            for name, value in attributes:
                if name == 'id' and value == 'thumbs':
                    self.recording = True

        elif tag == 'a' and self.recording:
            for name, value in attributes:
                if name == 'href':
                    self.data.append(value)


    def handle_endtag(self, tag):

        if tag == 'div':
            self.recording = False


class UserPagesParser(HTMLParser):

    def __init__(self):

        HTMLParser.__init__(self)

        self.data = list()
        self.urlflag = False
        self.nameflag = False

        self.regexp = '^http://www.metarthunter.com/content/[0-9]+/[a-zA-Z0-9\-]+.jpg$'


    def handle_starttag(self, tag, attributes):

        if tag == 'div':
            for name, value in attributes:
                if name == 'id' and value =='thumb01':
                    self.urlflag = True

        elif tag == 'a' and self.urlflag:
            for name, value in attributes:
                if name == 'href' and search(self.regexp, value) is not None: 
                    self.data.append(value)




if __name__ == '__main__':

    cfg = ConfigParser.ConfigParser()
    cfg.read('InstaMetart.conf')

    level = cfg.get('main', 'level')
    domain = cfg.get('main', 'domain')
    data_directory = cfg.get('main', 'data_directory')
    root_directory = os.path.split(os.path.abspath(sys.argv[0]))[0]

    max_processes = cfg.getint('main', 'max_processes')

    cache_file_name = cfg.get('cache', 'cache_file')
    cache_file = '%s/%s' % (root_directory, cache_file_name)

    url_cache = dict()
    image_urls_queue = list()


    if os.path.exists(data_directory) is not True:
        running_command('mkdir -p %s' % data_directory)

    if os.path.exists(cache_file):
        f = open(cache_file, 'r')
        for line in f.readlines():
            line = line.rstrip().split(',')
            url_cache[line[0]] = line[1]
        f.close()

    logging(level, 'Load Page Cache: %s Pages.\n' % len(url_cache))

    logging(level, 'Start Parser Page.\n')

    number=0
    f = open(cache_file, 'a')
    while(1):

        number = number + 1
        page_url = 'http://%s/page/%s' % (domain, number)
        
        index_page_parser = IndexPagesParser()
        try:
            url_open = urlopen(page_url)
            encoding = url_open.headers.getparam('charset')
        except Exception:
            pass
        index_page_parser.feed(url_open.read().decode(encoding))
        user_page_urls = index_page_parser.data
        index_page_parser.close()

        if len(user_page_urls) == 0:
            break

        for user_page_url in user_page_urls:

            user_page_url_md5 = hashlib.new('md5', user_page_url).hexdigest()

            if url_cache.get(user_page_url_md5) is None:

                logging(level, '\tStart Parser Page: %s, %s, %s\n' % (number, user_page_url_md5, user_page_url))

                #f.write('%s,%s\n' % (user_page_url_md5, user_page_url))

                user_page_parser = UserPagesParser()
                url_open = urlopen(user_page_url)
                encoding = url_open.headers.getparam('charset')
                user_page_parser.feed(url_open.read().decode(encoding))
                image_urls = user_page_parser.data
                user_page_parser.close()
                image_urls_queue.extend(image_urls)

                for image_url in image_urls:
                    image_url_md5 = hashlib.new('md5', image_url).hexdigest()
                    #f.write('%s,%s\n' % (image_url_md5, image_url))

    f.close()
    image_number = len(image_urls_queue)
    logging(level, 'Parser Finish, Altogether %s Images\n' % image_number)
    if image_number == 0:
        logging(level, 'No new pictures, exit!\n')
    elif image_number > 0:

        logging(level, 'Start to download new pictures!\n')
        pool = Pool(processes=max_processes)

        for image_url in image_urls_queue:

            image_name = image_url.split('/')[-1]
            command = 'wget -q -O %s%s %s' % (data_directory, image_name, image_url)
            pool.apply_async(running_command, (command, ))

        pool.close()
        pool.join()

        logging(level, 'Download images successful!\n')
