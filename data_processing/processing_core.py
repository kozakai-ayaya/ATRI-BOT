#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
@module  : processing_core.py
@author  : ayaya
@contact : minami.rinne.me@gmail.com
@time    : 2022/3/25 9:11 下午
"""
import json
import time

import pymysql
from typing import List

import requests

from atri_bot.twitter.tw import start_observe_tweets
from data_processing.common.Riko import Riko
from data_processing.common.connect import Connect
from data_processing.common.setting import PROFILE_IMAGE_PATH, TWITTER_URL, HEADERS, MEDIA_IMAGE_PATH


class ProcessingCore(object):
    def __init__(self):
        with open("atri_bot_db.json.json", "r") as file:
            config = json.loads(file.read())
        config["cursorclass"] = pymysql.cursors.DictCursor
        Riko.db_config = config

        self.connect = Connect()
        self.spider_user_list = list()

    def _read_user_list_in_txt(self) -> list:
        new_spider_user_list = []
        with open("spider_user_list.txt") as file:
            user_name = file.readline().replace("@", "")
            if user_name not in self.spider_user_list:
                new_spider_user_list.append(user_name)

        return new_spider_user_list

    def _check_spider_update_status(self) -> list:
        need_update_spider_user_list = []
        spider_user_info_in_db = [username for username in self.connect.get_spider_user_info()["username"]]

        for username in spider_user_info_in_db:
            update_dict = {"last_check_time": time.time()}
            self.connect.update_spider_user_info(username=username, info_dict=update_dict)

        for spider_user_info in self.spider_user_list:
            if spider_user_info not in spider_user_info_in_db:
                need_update_spider_user_list.append(spider_user_info)

        return need_update_spider_user_list

    def _save_profile_image(self, image_url: str) -> str:
        request = requests.get(url=image_url, headers=HEADERS)
        image_path = f"{PROFILE_IMAGE_PATH}/{image_url.split('/')[-1]}"

        if request.status_code == "200":
            with open(image_path, "wb") as file:
                file.write(request.content)
        else:
            image_path = None

        return image_path

    def _save_media_file(self, media_url: str, media_type: str) -> str:
        request = requests.get(url=media_url, headers=HEADERS)
        image_path = None

        if media_type == "photo":
            image_path = f"{MEDIA_IMAGE_PATH}/{media_url.split('/')[-1]}"
            if request.status_code == "200":
                with open(image_path, "wb") as file:
                    file.write(request.content)
            else:
                image_path = None
        elif media_type == "video":
            pass

        return image_path

    def _download_video(self):
        pass

    def update_new_spider_user_info(self, need_update_list: list, need_update_info: List[dict]) -> None:
        for flag_number in range(0, len(need_update_list)):
            user_info = need_update_info[flag_number]
            user_name = need_update_list[flag_number]

            self.connect.insert_spider_user_info(
                uid=user_info.get("uid"),
                user_name=user_name,
                last_check_time=user_info.get("created_at")
            )

            self.connect.insert_user_info(
                uid=user_info.get("uid"),
                name=user_info.get("user").get("name"),
                user_name=user_name,
                description=user_info.get("user").get("description"),
                profile_image_url=user_info.get("user").get("profile_image_url"),
                profile_image_path=self._save_profile_image(user_info.get("user").get("profile_image_url")),
                last_check_time=user_info.get("created_at")
            )

            self.update_new_text_info(need_update_info=need_update_info)

    def update_new_text_info(self, need_update_info: List[dict]) -> None:
        for text_info in need_update_info:
            twitter_url = f"{TWITTER_URL}/{text_info.get('user').get('username')}/status/{text_info.get('tid')}"

            self.connect.insert_message_info(
                tid=text_info.get("tid"),
                uid=text_info.get("uid"),
                name=text_info.get("user").get("name"),
                username=text_info.get("user").get("username"),
                text=text_info.get("text"),
                time=text_info.get("created_at"),
                tiw_url=twitter_url,
                tag=str(text_info.get("hashtags")),
                media_url=text_info.get("media").get("url"),
                media_key=text_info.get("media").get("type"),
                media_path=self._save_media_file(text_info.get("media").get("url"), text_info.get("media").get("type")),
                status=0,
                enter_time=time.time()
            )


    def get_message(self):
        self.spider_user_list = self._read_user_list_in_txt()
        need_update_spider_user_list = self._check_spider_update_status()

        if len(need_update_spider_user_list) != 0:
            start_observe_tweets(self.spider_user_list,
                                 lambda twitters: self.update_new_spider_user_info(need_update_spider_user_list,
                                                                                   twitters))

        start_observe_tweets(self._read_user_list_in_txt(), lambda twitters: self.update_new_text_info(twitters))

    def send_message(self):
        need_send_message_list = self.connect.get_message_info_by_status(status=0)
        self.connect.update_message_info_by_status(status=0, info_dict={"send_time": time.time()})
        return need_send_message_list

