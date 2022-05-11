import datetime
import functools
import json
import pickle
from enum import Enum
from http.cookiejar import MozillaCookieJar
from os import PathLike
from typing import Callable, Dict, Iterable, Optional, Tuple

import requests

from ..errors import AuthException, UnexpectedResponseException
from ..utils import PathOrStream, prepare_session


class WeiboVisible(Enum):
    EVERYONE = 0
    ONLY_TO_YOURSELF = 1
    ONLY_TO_FRIEND = 6


class WeiboAuth(requests.auth.AuthBase):
    def __init__(self, weibo_api):
        self.weibo_api = weibo_api

    def __call__(self, r):
        token = self.weibo_api.session.cookies.get("XSRF-TOKEN")
        if token:
            r.headers["x-xsrf-token"] = token
        return r


def set_referer(url, override=True):
    def wrapper_maker(func):
        @functools.wraps(func)
        def wrapper(self: WeiboAPIBase, *args, **kwargs):
            origin_referer = self.session.headers.get("referer")
            if not override and origin_referer:
                return func(self, *args, **kwargs)
            self.session.headers["referer"] = url
            try:
                return func(self, *args, **kwargs)
            finally:
                if origin_referer:
                    self.session.headers["referer"] = origin_referer
                else:
                    self.session.headers.pop("referer")

        return wrapper

    return wrapper_maker


def handel_json_with_ok(json_data: Dict) -> Tuple[bool, Dict]:
    if json_data.get("ok") is not None and json_data["ok"] != 1:
        return False, {}
    return True, json_data.get("data") or json_data.get("msg") or json_data


def json_response(matcher: Callable[[Dict], Tuple[bool, Dict]] = handel_json_with_ok):
    def wrapper_maker(func):
        @functools.wraps(func)
        def wrapper(self: WeiboAPIBase, *args, **kwargs) -> dict:
            # replace header value of Accept for higher priority of json reponse
            origin_accept = self.session.headers.get("Accept")
            self.session.headers["Accept"] = "application/json, text/plain, */*"
            try:
                response = func(self, *args, **kwargs)
                response_json = response.json()
            except json.JSONDecodeError as e:
                raise UnexpectedResponseException(response) from e
            finally:
                if origin_accept:
                    self.session.headers["Accept"] = origin_accept
                else:
                    self.session.headers.pop("Accept")

            ok, response_json = matcher(response_json)
            if not ok:
                raise UnexpectedResponseException(response)

            return response_json

        return wrapper

    return wrapper_maker


def need_login(func):
    @functools.wraps(func)
    def wrapper(self: WeiboAPIBase, *args, **kwargs):
        try:
            self.config
        except UnexpectedResponseException as e:
            raise AuthException() from e
        return func(self, *args, **kwargs)

    return wrapper


class WeiboAPIBase:
    def __init__(self):
        self.session = requests.Session()

        self._config = None
        self._config_update_time = None

    @property
    def config(self):
        """获取登录信息，更新xsrf token。正常情况下没有必要读取这个字段。"""
        if (
            self._config
            and self._config_update_time - datetime.datetime.now()
            < datetime.timedelta(minutes=5)
        ):
            return self._config
        self._config = self._get_config()
        self._config_update_time = datetime.datetime.now()
        return self._config

    def _get_config(self):
        raise NotImplementedError()

    def init_session(self, timeout: int = 10, proxies: Optional[Dict[str, str]] = None):
        prepare_session(self.session, timeout, proxies)

    def send_weibo(
        self,
        text: str,
        image_paths: Optional[Iterable[PathOrStream]] = None,
        visible: WeiboVisible = WeiboVisible.EVERYONE,
    ):
        raise NotImplementedError()

    def upload_image(self, path_or_stream: PathOrStream):
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
            instance.session.cookies, cookies_txt
        )
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
        for c in cookies_str.split("; "):
            k, v = c.split("=", 1)
            cookie = requests.cookies.create_cookie(
                k, v, domain=cls.cookies_key_to_domain(k)
            )
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
        with open(path, "r") as fp:
            cookies = requests.utils.cookiejar_from_dict(json.load(fp))
            instance.session.cookies.update(cookies)
        instance.init_session()
        return instance

    def save_cookies_json(self, path: str):
        """将cookies保存为可读的json，由于会丢失大量的信息，只推荐debug中使用。

        Args:
            path (str): json保存路径
        """
        with open(path, "w") as fp:
            json.dump(requests.utils.dict_from_cookiejar(self.session.cookies), fp)

    @classmethod
    def load_from_cookies_object(cls, path, **session_config):
        """读取cookiesjar二进制格式的cookies。推荐使用这个方法来读取cookies。

        Args:
            path (str): cookiesjar二进制格式读取路径
        """
        instance = cls()
        with open(path, "rb") as fp:
            cookies = pickle.load(fp)

        instance.session.cookies.update(cookies)

        instance.init_session(**session_config)
        return instance

    def save_cookies_object(self, path):
        """保存cookies到cookiesjar二进制格式。推荐使用这个方法来保存cookies。

        Args:
            path (str): cookiesjar二进制格式保存路径
        """
        with open(path, "wb") as fp:
            pickle.dump(self.session.cookies, fp)
