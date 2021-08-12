import enum
import re
import json
import time
import argparse
import requests
import pathlib2
import time
import random 
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

#mysql에 댓글 저장 원할 시 밑의 주석 해제
#import pymysql
#from config.mysql_config import mysql_info


def getPage(url):
    req = requests.get(url)
    return BeautifulSoup(req.text, 'html.parser')


def get_all_webtoon_links(url):
    bs = getPage(url)
    all_webtoon_links = []

    for daily_webtoons in bs.find_all('div', {'class': 'col'}):
        for webtoon in daily_webtoons.find_all('div', {'class': 'thumb'}):
            webtoon_link = webtoon.find('a')['href']
            all_webtoon_links.append(webtoon_link)
    return all_webtoon_links


def get_title(url):
    bs = getPage(url)
    title = bs.find('title').get_text().split(':')[0]
    return title


def get_titleId(url):
    return parse_qs(urlparse(url).query)['titleId'][0]


def get_all_episode_link(url, number_of_episode, is_latest):
    bs = getPage(url)
    last_episode_link = bs.find('td', {'class':'title'}).find('a')['href']
    last_episode_no = int(parse_qs(urlparse(last_episode_link).query)['no'][0])
    all_episode_link = []
    reg = re.compile('no=.*&')
    if number_of_episode == -1:
        number_of_episode = last_episode_no

    if is_latest:
        last_no = last_episode_no if last_episode_no <= number_of_episode else number_of_episode
        epi_range = range(1, last_no+1)
        all_episode_link = [re.sub(reg, 'no=' + str(i) + '&', last_episode_link) for i in epi_range]
    else:
        epi_range = range(last_episode_no, last_episode_no-(number_of_episode), -1)
        all_episode_link = [re.sub(reg, 'no=' + str(i) + '&', last_episode_link) for i in epi_range if i > 0]
    return all_episode_link


def get_episode_no(url):
    return parse_qs(urlparse(url).query)['no'][0]


def save_comments(title, titleId, episode_no):
    def remove_newlines(text):
        return re.sub(' +', ' ',text.replace('\n', ' '))

    comment_page = 1
    all_comments = []
    key_list = ['userIdNo', 'userName', 'maskedUserId', 'commentNo', 'parentCommentNo', 
    'contents', 'sympathyCount', 'antipathyCount', 'replyLevel', 'replyAllCount','regTime']
    while True:
        commentList = get_commentList(title, titleId, episode_no, comment_page)
        # print("loop", comment_page)
        if commentList:
            for comment in commentList:
                filtered_comment = dict((k, str(comment[k])) for k in key_list if k in comment)
                filtered_comment['contents'] = remove_newlines(filtered_comment['contents'])
                all_comments.append('\t'.join(filtered_comment.values()))
                if len(all_comments) % 30000 == 0:
                    write_all_comments(title, episode_no, all_comments)
                    all_comments = []
        else:
            # mysql에 댓글 저장 원할 시 밑의 주석 해제
            #send_mysql(title, episode_no, all_comments)
            write_all_comments(title, episode_no, all_comments)
            return
        comment_page = comment_page + 1
        
        
def write_all_comments(title, episode_no, all_comments):
    pathlib2.Path(OUTPUT_PATH).mkdir(exist_ok=True, parents=True)
    comment_file_name = os.path.join(OUTPUT_PATH, COMMENT_FILE_NAME)
    f = open(comment_file_name, 'a', encoding="utf-8")
    try:
        for comment in all_comments:
            f.write(title + '\t' + episode_no + '\t' + comment + "\n")
    finally:
        f.close()



def get_episode_info(title, titleId, episode_no):
    url = 'https://comic.naver.com/webtoon/detail?titleId={titleId}&no={no}'.format(titleId=titleId, no=episode_no)
    bs = getPage(url)
    box_info = bs.find('div', {'class': 'tit_area'})
    episode_name = box_info.find('h3').get_text()
    
    episode_rating = box_info.find('span', {'id': 'topPointTotalNumber'}).find('strong').get_text()
    episode_total_users = box_info.find('span', {'class': 'pointTotalPerson'}).find('em').get_text()

    episode_reg_date = box_info.find('dl', {'class': 'rt'}).find('dd', {'class': 'date'}).get_text()
    episode_info = [title, titleId, url, episode_name, episode_rating, episode_total_users, episode_reg_date]
    return episode_info
    

def write_episode_info(episode_info):
    pathlib2.Path(OUTPUT_PATH).mkdir(exist_ok=True, parents=True)
    episode_file_name = os.path.join(OUTPUT_PATH, EPISODE_FILE_NAME)
    f = open(episode_file_name, 'a', encoding="utf-8")
    try:
        episode_info = '\t'.join(episode_info)
        f.write(episode_info + "\n")
    finally:
        f.close()



def save_episode_info(title, titleId, episode_no):
    episode_info = get_episode_info(title, titleId, episode_no)
    write_episode_info(episode_info)
    return


def get_commentList(title, titleId, episode_no, comment_page):
    ajax_link = 'https://apis.naver.com/commentBox/cbox/web_naver_list_jsonp.json?ticket=comic&templateId=webtoon' + \
                '&pool=cbox3&_callback=jQuery112409768039369695578_1588773317723&lang=ko&country=KR&objectId=' + \
                titleId + '_' + episode_no + '&categoryId=&pageSize=100&indexSize=10&groupId=&listType=OBJECT&pageType=default&page=' + str(comment_page) + \
                '&refresh=true&sort=new&cleanbotGrade=2&_=1588773317725'
    custom_header = {
        'referer': 'https://comic.naver.com/comment/comment.nhn?titleId=' + titleId + '&no=' + episode_no,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36'
    }
    req = requests.get(ajax_link, headers=custom_header).text
    json_req = json.loads(req[req.find("success") - 2:len(req) - 2])
    commentList = json_req['result']['commentList']
    return commentList


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--number_of_episode', required=False, default=51)

#     args = parser.parse_args()

#     naver_webtoon_link = 'https://comic.naver.com'
#     naver_webtoon_list_link = 'https://comic.naver.com/webtoon/weekday.nhn'
#     all_webtoon_links = get_all_webtoon_links(naver_webtoon_list_link)

#     for index, webtoon_link in enumerate(all_webtoon_links):
#         absolute_path = naver_webtoon_link + webtoon_link
#         title = get_title(absolute_path)
#         titleId = get_titleId(absolute_path)
#         all_episode_link = get_all_episode_link(absolute_path, int(args.number_of_episode))
#         print("===== [", index, "] ", title)
#         for episode_link in all_episode_link:
#             episode_no = get_episode_no(episode_link)
#             print(title, episode_no)
#             comments = save_comments(title, titleId, episode_no)
#             random_t = random.uniform(0.9, 1.3)
#             print("Sleep {} seconds from now on...".format(random_t))
#             time.sleep(random_t)
#         time.sleep(random.uniform(59, 66))


if __name__ == "__main__":

    OUTPUT_PATH = './data'
    COMMENT_FILE_NAME = 'naver_webtoon_comments.txt'
    EPISODE_FILE_NAME = 'naver_webtoon_episode_info.txt'

    parser = argparse.ArgumentParser()
    parser.add_argument('--number_of_episode', required=False, default=10)
    parser.add_argument('--is_latest', required=False, default=False)
    args = parser.parse_args()

    naver_webtoon_link = 'https://comic.naver.com'
    naver_webtoon_list_link = 'https://comic.naver.com/webtoon/weekday.nhn'
    all_webtoon_links = get_all_webtoon_links(naver_webtoon_list_link)
    for index, webtoon_link in enumerate(all_webtoon_links):
        if index > 1:
            continue
        absolute_path = naver_webtoon_link + webtoon_link
        title = get_title(absolute_path)
        titleId = get_titleId(absolute_path)
        all_episode_link = get_all_episode_link(absolute_path, int(args.number_of_episode), int(args.is_latest))
        print("===== [", index, "] ", title)
        for episode_link in all_episode_link:
            episode_no = get_episode_no(episode_link)
            print(title, episode_no)

            # save comments
            save_comments(title, titleId, episode_no)

            # save episode infomation
            save_episode_info(title, titleId, episode_no)
            episode_info = get_episode_info(title, titleId, episode_no)
            write_episode_info(episode_info)
            random_t = random.uniform(0.9, 1.3)
            print("Sleep {} seconds from now on...".format(random_t))
            time.sleep(random_t)
        time.sleep(random.uniform(59, 66))