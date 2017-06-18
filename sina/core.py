#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2017 lizongzhe
#
# Distributed under terms of the MIT license.
import requests
from datetime import datetime, timedelta
import json
from bs4 import BeautifulSoup, Comment
import re
from gevent.pool import Pool
import gevent.monkey
gevent.monkey.patch_socket()
import os
import logging
from logging.config import fileConfig
from gevent.queue import Queue

output_queue = Queue()

current_path = os.path.dirname(os.path.abspath(__file__))
fileConfig(os.path.join(current_path, 'logging_config.ini'))

logger = logging.getLogger()

league_years = [
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017"
]


league_infos = [
  {
    "sl_league_type": "213",
    "name": "英超",
    "cur_rnd": "30",
    "current_league": "2016",
    "max_rnd": "30",
#    "id": "8"
  },
  {
    "sl_league_type": "1",
    "name": "意甲",
    "cur_rnd": "38",
    "current_league": "2016",
    "max_rnd": "38",
    "id": "21"
  },
  {
    "sl_league_type": "3",
    "name": "德甲",
    "cur_rnd": "34",
    "current_league": "2016",
    "max_rnd": "34",
    "id": "22"
  },
  {
    "sl_league_type": "2",
    "name": "西甲",
    "cur_rnd": "38",
    "current_league": "2016",
    "max_rnd": "38",
    "id": "23"
  },
  {
    "sl_league_type": "5",
    "name": "法甲",
    "cur_rnd": "38",
    "current_league": "2016",
    "max_rnd": "38",
    "id": "24"
  },
  {
    "sl_league_type": "4",
    "name": "英超",
    "cur_rnd": "38",
    "current_league": "2016",
    "max_rnd": "38",
    "id": "8"
  },
]

def get(url):
    logger.info("get {}".format(url))
    try:
        if url == "http://admin.match.sports.sina.com.cn/app/home/index.php":
            return
        return requests.get(url, timeout=10)
    except Exception as e:
        logger.exception(e)
        return get(url)


def crawl_rnd_info():
    now = datetime.now()
#    data = get(
#        'http://platform.sina.com.cn/sports_all/client_api?_sport_t_=Intlfootball&_sport_a_=getLeaguesInfo&callback=&app_key=3571367214&_={:%s}'.format(now)).json()
#    result = data['result']['data'].values()
    result = league_infos

    info_url = "http://platform.sina.com.cn/sports_all/client_api?_sport_t_=livecast&_sport_a_=matchesByType&app_key=3571367214&type={type}&rnd={rnd}&season={year}&_={t:%s}"
    for info in result:
        sl_league_type = info['sl_league_type']
        max_rnd = int(info['max_rnd'])
        # league_id = info['id']
        for year in league_years:
            for rnd in range(1, max_rnd + 1):
                url = info_url.format(
                    year=year, type=sl_league_type, rnd=rnd, t=now)
                # rnd_data = get(url)
                data = {}
                data['name'] = info['name']
                data['year'] = year
                data['rnd'] = rnd
                data['url'] = url
                yield data


def crawl_game_infos():
    for rnd_info in crawl_rnd_info():
        print rnd_info
        url = rnd_info['url']
        games_info = get(url).json()
        print "start rnd download"
        for game_info in games_info['result']['data']:
            yield game_info
        print "end rnd download"

def get_article(url):
    battlefield_report = get(url).content

    if battlefield_report.find('HTTP-EQUIV="Refresh"') != -1:
        new_url = re.findall('URL=([^"]*)', battlefield_report)[0]
        logger.info("{} to {}".format(url, new_url))
        battlefield_report = get(new_url).content

    try:
        battlefield_report = battlefield_report.decode('utf-8')
    except:
        battlefield_report = battlefield_report.decode(
            'gb2312', errors='ignore')

    soup = BeautifulSoup(battlefield_report)

    extract_tag(soup)
    if soup.select('article'):
        article_html = unicode(soup.select('article')[0])
    elif soup.select('.blkContainerSblk'):
        article_html = unicode(soup.select('.blkContainerSblk')[0])
        article_html = re.sub("\n+", "\n", article_html)
    else:
        article_html = ""
        print 'article parse error {}'.format(url)
    
    return article_html

def procese_game_info(game_info):
    data = game_info
    game_id = game_info['livecast_id']
    game_log = get_game_tracking_log(game_id)
    game_players = get_game_players(game_id)
    game_event_classify = get_game_event_classify(game_id)
    match_event = get_game_matchevent(game_id)
    if game_info.get('NewsUrl', None):
        logger.info('redirect')
        logger.info(game_info['NewsUrl'])
        article_html = get_article(game_info['NewsUrl'])
    else:
        article_html = ""

    data['article_html'] = article_html
    data['players'] = game_players
    data['tracking_log'] = game_log
    data['event_classify'] = game_event_classify
    data['match_event'] = match_event

    output_queue.put(data)


def get_game_players(game_id):
    url = "http://platform.sina.com.cn/sports_all/client_api?app_key=3749442444&_sport_t_=football&_sport_s_=opta&_sport_a_=teamformation&id={}&dpc=1"
    return get(url.format(game_id)).json()['result']['data']


def get_game_event_classify(game_id):
    url = "http://platform.sina.com.cn/sports_all/client_api?app_key=3749442444&_sport_t_=f24&_sport_a_=pktop&match_id={}&type=all&dpc=1"
    return get(url.format(game_id)).json()['result']['data']


def get_game_tracking_log(id):
    url = 'http://platform.sina.com.cn/sports_all/client_api?app_key=3749442444&_sport_t_=livecast&_sport_a_=livelog&id={id}&nolink=0&order=1&num=1500&dpc=1'

    resp = get(url.format(id=id))
    result = json.loads(resp.content)

    first_half = u"上半場"
    second_half = u"下半場"
    done = u"完賽"

    r = []
    for d in result['result']['data']:
        if d['s'] == u'上':
            section = first_half
            try:
                d['t'] = d['t'] or "0"
                time = int(d['t'].replace("'", "")) * 60
            except:
                pass
        if d['s'] == u"下":
            section = second_half
            d['t'] = d['t'] or "0"
            time = int(d['t'].replace("'", "")) * 60
        elif d['s'] == u"完赛":
            time = None
            section = done
        else:
            # inline pic
            continue

        message = d['m']
        soccor = u'%s-%s' % (d['s1'], d['s2'])

        r.append({
            'time': time,
            'message': u'%s %s' % (message, soccor),
            'data': d,
            'section': section
        })
    return r


def get_game_matchevent(id):
    url = 'http://platform.sina.com.cn/sports_all/client_api?app_key=3749442444&_sport_t_=f24&_sport_a_=matchevent&match_id={id}&dpce=1'

    resp = get(url.format(id=id))
    result = json.loads(resp.content)

    first_half = u"上半場"
    second_half = u"下半場"
    r = []
    for d in result['result']['data']:
        time = timedelta(minutes=int(d['minute']), seconds=int(
            d['second'])).total_seconds()
        message = d['desc']

        _type = d['event']

        if u'下半场' in message:
            section = second_half
            time -= 45 * 60

        elif u'上半场' in message:
            section = first_half

        r.append({
            "time": time,
            "message": message,
            'data': d,
            'type': _type,
            "section": section
        })
    return r


def extract_tag(soup):
    for script in soup.select('script'):
        script.extract()
    for style in soup.select('style'):
        style.extract()
    for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
        comment.extract()

def write_worker():
    count = 0 
    with open('result', 'w+') as f:
        while True:
            job = output_queue.get()
            if job == 'success':
                return
            if not job:
                continue
            f.write(json.dumps(job))
            f.write("\n")
            count += 1
            print count


f = open('result', 'w+')
c = 0
writer = gevent.spawn(write_worker)

pool = Pool(10)
pool.map(procese_game_info, crawl_game_infos())
output_queue.put('success')

writer.join()
