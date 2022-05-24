#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
@module  : processing_core.py
@author  : ayaya
@contact : minami.rinne.me@gmail.com
@time    : 2022/3/25 9:11 下午
"""
import copy
import json
import os
import random
import time
import concurrent.futures

from typing import List

import pymysql
import requests

from atri_bot.twitter.tw import start_observe_tweets, get_users, escape_regular_text
from atri_bot.weibo import WeiboAPI
from data_processing.common.Riko import Riko
from data_processing.common.connect import Connect
from data_processing.common.setting import (
    PROFILE_IMAGE_PATH,
    TWITTER_URL,
    HEADERS,
    MEDIA_IMAGE_PATH,
    MEDIA_VIDEO_PATH,
    WEIBO_COOKIES_PATH,
    WEIBO_COOKIES,
)

WEIBO_TEMPLATE = """{name}
(a){username}
{created_at}

{text}

{url}"""


class ProcessingCore(object):
    def __init__(self):
        with open("data_processing/atri_bot_db.json", "r") as file:
            config = json.loads(file.read())
        config["cursorclass"] = pymysql.cursors.DictCursor
        Riko.db_config = config

        self.connect = Connect()
        self._create_folder()
        self.spider_user_list = list()
        self.need_update_spider_user_list = list()
        self.error_user_list = list()
        self._init_start_user_list()

        WeiboAPI.load_from_cookies_str(WEIBO_COOKIES).save_cookies_object(
            WEIBO_COOKIES_PATH
        )
        self.weibo_api = WeiboAPI.load_from_cookies_object(WEIBO_COOKIES_PATH)
        self.executor = concurrent.futures.ThreadPoolExecutor(1) # WeiboAPI 不是线程安全的，不要调整worker数量

    def bot_star(self):
        start_observe_tweets(
            usernames=self.spider_user_list,
            callback=lambda twitters: self._bot_controller(twitters),
        )

    def _init_start_user_list(self) -> None:
        need_update_list = self._get_need_update_spider()
        text_list = self._read_user_list_in_txt()
        if len(need_update_list) == 0:
            self.spider_user_list = text_list
        else:
            self.need_update_spider_user_list = need_update_list
            self.spider_user_list = copy.deepcopy(need_update_list)

    def _create_folder(self) -> None:
        path_list = [PROFILE_IMAGE_PATH, MEDIA_IMAGE_PATH, MEDIA_VIDEO_PATH]
        for path in path_list:
            if not os.path.exists(path):
                os.mkdir(path)

    def _read_user_list_in_txt(self) -> list:
        text_spider_user_list = []
        with open("data_processing/spider_user.txt") as file:
            for text in file.readlines():
                user_name = text.replace("@", "").replace("\n", "")
                text_spider_user_list.append(user_name)

        return text_spider_user_list

    def _check_user_info_change(self, user_info_list: List[dict]):
        change_dict = dict()

        for user_info in user_info_list:
            check_user_info_list = get_users(user_info["uid"])[0]
            for key, value in check_user_info_list.iterm():
                if user_info[key] == value:
                    continue

                if key == "username":
                    self.connect.update_spider_user_info(
                        username=user_info[key],
                        info_dict={"username": check_user_info_list.get(key)},
                    )

                if key == "profile_image_url":
                    change_dict[key] = self._save_profile_image(
                        check_user_info_list[key]
                    )

                change_dict[key] = check_user_info_list.get(key)

            if len(change_dict) == 0:
                continue

            self.connect.update_user_info(uid=user_info["uid"], info_dict=change_dict)
            change_dict = dict()

    def _get_need_update_spider(self) -> list:
        need_update_spider_user_list = []
        spider_user_info_in_db = [
            db_info["username"] for db_info in self.connect.get_spider_user_info()
        ]
        user_info_in_db = [db_info["uid"] for db_info in self.connect.get_user_info()]

        if len(spider_user_info_in_db) != 0:
            for username in spider_user_info_in_db:
                update_dict = {
                    "last_check_time": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
                    )
                }
                self.connect.update_spider_user_info(
                    username=username, info_dict=update_dict
                )

        if len(user_info_in_db) != 0:
            for uid in user_info_in_db:
                update_dict = {
                    "last_check_time": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
                    )
                }
                self.connect.update_user_info(uid=uid, info_dict=update_dict)

        for spider_user_info in self._read_user_list_in_txt():
            if spider_user_info not in spider_user_info_in_db:
                need_update_spider_user_list.append(spider_user_info)

        return need_update_spider_user_list

    def _save_profile_image(self, image_url: str) -> str:
        request = requests.get(url=image_url, headers=HEADERS)
        image_path = f"{PROFILE_IMAGE_PATH}/{image_url.split('/')[-1]}"

        if request.status_code == 200:
            with open(image_path, "wb") as file:
                file.write(request.content)
        else:
            image_path = None

        return image_path

    def _save_media_file(self, media_url_list: list, media_type_list: list) -> list:
        image_path_list = list()

        for flag in range(len(media_url_list)):
            request = requests.get(url=media_url_list[flag], headers=HEADERS)
            image_path = None

            if len(media_url_list[flag]) == 0:
                continue

            if media_type_list[flag] == "photo":
                image_path = os.path.join(
                    MEDIA_IMAGE_PATH, media_url_list[flag].split("/")[-1]
                )
                if request.status_code == 200:
                    with open(image_path, "wb") as file:
                        file.write(request.content)
                else:
                    image_path_list.append("")
            elif media_type_list[flag] == "video":
                pass

            image_path_list.append(image_path)

        return image_path_list

    def _download_video(self):
        pass

    def _get_media_url_info(self, media_data: List[dict], get_key: str) -> list:
        media_data_list = list()

        if len(media_data) == 0:
            return []

        for data in media_data:
            media_value = data.get(get_key)
            if media_value is None or media_value == "":
                continue
            media_data_list.append(media_value)

        return media_data_list

    def _check_hashtag(self, hash_tag: List[dict]) -> object:
        if hash_tag is None:
            return None

        return str(hash_tag)[1:-1]

    def update_new_spider_user_info(self, users_list: list) -> None:
        users_info_list = get_users(users_list)
        for user in users_info_list:
            try:
                self.connect.insert_spider_user_info(
                    uid=user.get("id"),
                    username=user.get("username"),
                    add_time=time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
                    ),
                )
            except pymysql.err.IntegrityError:
                pass

            try:
                self.connect.insert_user_info(
                    uid=user.get("id"),
                    name=user.get("name"),
                    username=user.get("username"),
                    description=user.get("description"),
                    profile_image_url=user.get("profile_image_url"),
                    profile_image_path=self._save_profile_image(
                        user.get("profile_image_url")
                    ),
                    add_time=time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
                    ),
                )

            except pymysql.err.IntegrityError:
                pass

    def update_new_text_info(self, need_update_info: List[dict]) -> None:
        for text_info in need_update_info:
            twitter_url = f"{TWITTER_URL}/{text_info.get('user').get('username')}/status/{text_info.get('tid')}"

            try:
                self.connect.insert_message_info(
                    tid=text_info.get("tid"),
                    uid=text_info.get("uid"),
                    name=text_info.get("user").get("name"),
                    username=text_info.get("user").get("username"),
                    text=text_info.get("text"),
                    time=text_info.get("created_at"),
                    twi_url=twitter_url,
                    tag=self._check_hashtag(text_info.get("hashtags")),
                    media_url=",".join(
                        self._get_media_url_info(text_info.get("media"), "url")
                    ),
                    media_key=",".join(
                        self._get_media_url_info(text_info.get("media"), "type")
                    ),
                    media_path=",".join(
                        self._save_media_file(
                            self._get_media_url_info(text_info.get("media"), "url"),
                            self._get_media_url_info(text_info.get("media"), "type"),
                        )
                    ),
                    status=0,
                    enter_time=time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
                    ),
                )
            except pymysql.err.IntegrityError:
                continue

    def _update_send_message_status(self, message_status: dict) -> None:

        info_dict = {
            "status": message_status.get("status"),
            "send_time": time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(time.time()),
            ),
        }

        if message_status.get("status") == -1:
            info_dict["error_message"] = message_status.get("error_message")

        self.connect.update_message_info_by_tid(
            tid=message_status.get("tid"), info_dict=info_dict
        )

    def send_message(self):
        message_list = self.connect.get_message_info_by_status(status=0)

        for m in message_list:
            def run():
                try:
                    self.weibo_api.send_weibo(
                        WEIBO_TEMPLATE.format_map(
                            {
                                "name": m.get("name"),
                                "username": escape_regular_text(m.get("username")),
                                "created_at": m.get("time"),
                                "text": m.get("text"),
                                "url": m.get("twi_url"),
                            }
                        ),
                        m.get('media_path').split(',') if m.get('media_path') else None,  # TODO: 不支持视频，需要额外检查
                    )
                    self._update_send_message_status({"tid": m["tid"], "status": 1})
                except Exception as err:
                    self._update_send_message_status(
                        {"tid": m["tid"], "status": -1, "error_message": err}
                    )
            
            self.executor.submit(run)

    def _bot_controller(self, twitters: List[dict]):

        update_spider_user_list = self._get_need_update_spider()

        if len(update_spider_user_list) != 0:
            self.update_new_spider_user_info(self.spider_user_list)
            self.need_update_spider_user_list = copy.deepcopy(update_spider_user_list)
            start_observe_tweets(
                usernames=update_spider_user_list,
                max_results=20,
                callback=lambda twitter: self._bot_controller(twitter),
            )

        if len(self.need_update_spider_user_list) != 0:
            self.spider_user_list.extend(self.need_update_spider_user_list)
            self.need_update_spider_user_list.clear()

        self.update_new_text_info(twitters)
        self.send_message()

        start_observe_tweets(
            usernames=self.spider_user_list,
            interval=60,
            max_results=10,
            callback=lambda twitter: self._bot_controller(twitter),
        )

    def error_user(self, error_user_list: list):
        pass


if __name__ == "__main__":
    ProcessingCore().bot_star()
