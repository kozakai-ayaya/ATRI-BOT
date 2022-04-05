#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
@module  : connect.py
@author  : ayaya
@contact : minami.rinne.me@gmail.com
@time    : 2022/3/25 9:34 下午
"""
from data_processing.common.Riko import DictModel


class message(DictModel):
    pk = ["id"]
    fields = ["tid", "uid", "name", "username", "text", "time", "tiw_url", "tag", "media_url", "media_key",
              "media_type", "media_path", "status", "send_time", "enter_time"]


class spider_user(DictModel):
    pk = ["id"]
    fields = ["uid", "username", "add_time", "add_time", "last_check_time"]


class user(DictModel):
    pk = ["id"]
    fields = ["uid", "name", "username", "description", "profile_image_url", "profile_image_path", "add_time",
              "update_time", "last_check_time"]


class Connect(object):
    def __init__(self):
        pass

    @staticmethod
    def insert_message_info(**kwargs):
        message.new(**kwargs).insert()

    @staticmethod
    def get_message_info_by_status(status: int):
        get_info = message.select().where_raw("status = %(input_status)s").get({"input_status": status})
        return get_info

    @staticmethod
    def get_message_info_by_username_and_status(username: str, status: int):
        get_info = message.select() \
            .where_raw("username = %(input_username)s AND status = %(input_status)s") \
            .get({"input_username": username, "input_status": status})
        return get_info

    @staticmethod
    def update_message_info_by_tid_and_update(tid: str, status: int, info_dict: dict):
        new_info = message.select() \
            .where_raw("status = %(input_status)s").get({"input_status": status})
        for k, v in info_dict.items():
            new_info[k] = v
        new_info.update()

    @staticmethod
    def update_message_info_by_username_and_status(username: str, status: int, info_dict: dict):
        new_info = message.select() \
            .where_raw("username = %(input_username)s AND status = %(input_status)s") \
            .get({"input_username": username, "input_status": status})
        for k, v in info_dict.items():
            new_info[k] = v
        new_info.update()

    @staticmethod
    def insert_spider_user_info(**kwargs):
        spider_user.new(**kwargs).insert()

    @staticmethod
    def get_spider_user_info():
        get_info = spider_user.get_many()
        return get_info

    @staticmethod
    def update_spider_user_info(username: str, info_dict: dict):
        new_info = spider_user.get_one(username=username)
        for k, v in info_dict.items():
            new_info[k] = v
        new_info.update()

    @staticmethod
    def insert_user_info(**kwargs):
        user.new(**kwargs).insert()

    @staticmethod
    def get_user_info():
        get_info = user.get_many()
        return get_info

    @staticmethod
    def update_user_info():
        pass

