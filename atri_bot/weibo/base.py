
import json
import pickle
from enum import Enum
from http.cookiejar import MozillaCookieJar
from io import IOBase
from os import PathLike
from typing import Optional, Union

import requests

from ..utils import prepare_session


class WeiboVisible(Enum):
    EVERYONE = 0
    ONLY_TO_YOURSELF = 1
    ONLY_TO_FRIEND = 6


class WeiboAuth(requests.auth.AuthBase):
    def __init__(self, weibo_api):
        self.weibo_api = weibo_api

    def __call__(self, r):
        token = self.weibo_api.session.cookies.get('XSRF-TOKEN')
        if token:
            r.headers['x-xsrf-token'] = token
        return r


class WeiboAPIBase:
    def __init__(self):
        self.session = requests.Session()

    def init_session(self, timeout: int = 10, proxies: dict[str, str] = None):
        prepare_session(self.session, timeout, proxies)

    def send_weibo(self,
                   text: str,
                   image_paths: Optional[Union[str, PathLike, IOBase]] = None,
                   visible: WeiboVisible = WeiboVisible.EVERYONE
                   ):
        raise NotImplementedError()

    def upload_image(self, path_or_io: Union[str, PathLike, IOBase]):
        raise NotImplementedError()

    @staticmethod
    def cookies_key_to_domain(key):
        # return '.m.weibo.cn' if key == 'XSRF-TOKEN' else '.weibo.cn'
        raise NotImplementedError()

    @classmethod
    def load_from_cookies_txt(cls, path: PathLike, **session_config):
        cookies_txt = MozillaCookieJar(path)
        cookies_txt.load()
        instance = cls()
        instance.session.cookies = requests.cookies.merge_cookies(
            instance.session.cookies, cookies_txt)
        instance.init_session(**session_config)
        return instance

    @classmethod
    def load_from_cookies_str(cls, cookies_str: str, **session_config):
        """从HTTP头中的cookies字段值直接加载cookies

        Args:
            cookies_str (str): HTTP头中的cookies字段值

        Returns:
            WeiboAPI:
        """
        instance = cls()
        cookies_jar = instance.session.cookies
        for c in cookies_str.split('; '):
            k, v = c.split("=", 1)
            cookie = requests.cookies.create_cookie(
                k, v, domain=cls.cookies_key_to_domain(k))
            cookies_jar.set_cookie(cookie)
        instance.init_session(**session_config)
        return instance

    @classmethod
    def load_cookies_json(cls, path):
        """加载json格式的cookies。由于会丢失大量的信息，只推荐debug中使用。

        Args:
            path (str): json读取路径
        """
        instance = cls()
        with open(path, 'r') as fp:
            cookies = requests.utils.cookiejar_from_dict(json.load(fp))
            instance.session.cookies.update(cookies)
        instance.init_session()
        return instance

    def save_cookies_json(self, path: str):
        """将cookies保存为可读的json，由于会丢失大量的信息，只推荐debug中使用。

        Args:
            path (str): json保存路径
        """
        with open(path, 'w') as fp:
            json.dump(requests.utils.dict_from_cookiejar(
                self.session.cookies), fp)

    @classmethod
    def load_from_cookies_object(cls, path, **session_config):
        """读取cookiesjar二进制格式的cookies。推荐使用这个方法来读取cookies。

        Args:
            path (str): cookiesjar二进制格式读取路径
        """
        instance = cls()
        with open(path, 'rb') as fp:
            cookies = pickle.load(fp)

        instance.session.cookies.update(cookies)

        instance.init_session(**session_config)
        return instance

    def save_cookies_object(self, path):
        """保存cookies到cookiesjar二进制格式。推荐使用这个方法来保存cookies。

        Args:
            path (str): cookiesjar二进制格式保存路径
        """
        with open(path, 'wb') as fp:
            pickle.dump(self.session.cookies, fp)
