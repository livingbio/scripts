#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2017 lizongzhe 
#
# Distributed under terms of the MIT license.

from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
import time
import requests
import logging
import sys
import os

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)



def make_login_session(email, password):
    logger.info('loging start')
    driver = Chrome("/etc/chromedriver")
    try:
        driver.get('https://topbuzz.com/privacy')
        login_btn = driver.find_element_by_css_selector('.right-menu .btn-inline')
        logger.info('click login btn')
        login_btn.click()

        email_login_btn = WebDriverWait(driver, 10).until(
            lambda x:x.find_element_by_css_selector('.btn-email')
        )
        logger.info('click email login')
        email_login_btn.click()

        WebDriverWait(driver, 10).until(
            lambda x:x.find_element_by_css_selector('[placeholder=Email]')
        )

        logger.info('pass email & password')
        driver.execute_script("document.querySelector('[placeholder=Email]').value='{}'".format(email))
        driver.execute_script("document.querySelector('input.password').value='{}'".format(password))

        logger.info('submit')
        driver.find_element_by_css_selector('.tb-btn-primary').click()
        
        WebDriverWait(driver, 10).until(
                lambda x:not x.find_elements_by_css_selector(".signin-show")
        )

        cookies = dict([(c['name'], c['value']) for c in driver.get_cookies()])
        return cookies
    except Exception as e:
        logger.error(e)
        raise e
    finally:
        driver.close()
        pass



def download_video_analysis(email, password):
    cookies = make_login_session(email, password)
    page_size = 50
    page = 0
    offset = 0
    analysis_url = "https://topbuzz.com/pgc/article/stats?page={}&article_type=1&limit={}&offset={}"

    while True:
        url = analysis_url.format(page, page_size, offset)
        data = requests.get(url, cookies=cookies).json()
        page += 1
        offset = page * page_size
        
        try:
            data = data['data']['stats_data']
        except Exception as e:
            print data
            raise e

        if not data:
            return
        for d in data:
            yield d

    

if __name__ == '__main__':
    import sys
    import csv
    from datetime import datetime
    import json

    _, email, password, output = sys.argv

    base_path = os.path.dirname(output)
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    data = download_video_analysis(email, password)
    with open(output, 'w+') as f:
        for d in data:
            d.update({"date": datetime.today().strftime('%Y-%m-%d %H:%M:%S')})
            f.write(json.dumps(d))
            f.write("\n")
