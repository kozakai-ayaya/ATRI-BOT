import functools
import json
import pickle
import datetime
from os import PathLike
from pathlib import Path
from typing import Iterable, List, Optional

import requests

from . import urls

DEAFULT_HEADER = {
    'mweibo-pwa': '1',
    'x-requested-with': 'XMLHttpRequest',
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Mobile Safari/537.36 Edg/96.0.1054.62'
}


def encode_compose_refer(image_ids: List[str]):
    referer = urls.COMPOSE_REFERER_BASE
    if image_ids:
        referer += f'/?pids={",".join(image_ids)}'
    return referer


def set_referer(url, override=True):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped_func(self, *args, **kwargs):
            origin_referer = self.session.headers.get('referer')
            if not override and origin_referer:
                return func(self, *args, **kwargs)
            self.session.headers['referer'] = url
            try:
                return func(self, *args, **kwargs)
            finally:
                if origin_referer:
                    self.session.headers['referer'] = origin_referer
                else:
                    self.session.headers.pop('referer')
        return wrapped_func
    return wrapper


class WeiboAuth(requests.auth.AuthBase):
    def __init__(self, weibo_api):
        self.weibo_api = weibo_api

    def __call__(self, r):
        r.headers['x-xsrf-token'] = self.weibo_api.st
        return r


class WeiboApi:
    def __init__(self):
        self.session = requests.Session()
        self._prepare_session()

        self._config = None
        self._config_update_time = None

    def _prepare_session(self):
        self.session.headers.update(DEAFULT_HEADER)
        self.session.auth = WeiboAuth(self)

    @classmethod
    def load_from_cookies_str(cls, cookies_str: str):
        """从HTTP头中的cookies字段值直接加载cookies

        Args:
            cookies_str (str): HTTP头中的cookies字段值

        Returns:
            WeiboApi:
        """
        instance = WeiboApi()
        cookies_jar = instance.session.cookies
        for c in cookies_str.split(';'):
            k, v = c.split("=")
            k = k.strip()
            cookie = requests.cookies.create_cookie(
                k, v, domain='.m.weibo.cn' if k == 'XSRF-TOKEN' else '.weibo.cn')
            cookies_jar.set_cookie(cookie)
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
    def load_cookies_json(cls, path):
        """加载json格式的cookies。由于会丢失大量的信息，只推荐debug中使用。

        Args:
            path (str): json读取路径
        """
        instance = WeiboApi()
        with open(path, 'r') as fp:
            cookies = requests.utils.cookiejar_from_dict(json.load(fp))
            instance.session.cookies.update(cookies)
        return instance

    def save_cookies_object(self, path):
        """保存cookies到cookiesjar二进制格式。推荐使用这个方法来保存cookies。

        Args:
            path (str): cookiesjar二进制格式保存路径
        """
        with open(path, 'wb') as fp:
            pickle.dump(self.session.cookies, fp)

    @classmethod
    def load_from_cookies_object(c, path):
        """读取cookiesjar二进制格式的cookies。推荐使用这个方法来读取cookies。

        Args:
            path (str): cookiesjar二进制格式读取路径
        """
        instance = WeiboApi()
        with open(path, 'rb') as fp:
            cookies = pickle.load(fp)
        
        instance.session.cookies.update(cookies)
        _ = instance.config
        return instance

    @property
    def config(self):
        """获取登录信息，更新xsrf token，通常没有必要读取这个字段，可以直接使用is_login，st，uid字段。
        """
        if self._config and self._config_update_time - datetime.datetime.now() < datetime.timedelta(minutes=5):
            return self._config
        self._config = self._get_config()
        return self._config

    @set_referer(urls.BASE_URL)
    def _get_config(self):
        config_json = self.session.get(urls.CONFIG).json()
        assert config_json['ok'] == 1
        self._config_update_time = datetime.datetime.now()
        return config_json['data']

    @property
    def st(self):
        return self.session.cookies['XSRF-TOKEN']

    @property
    def is_login(self):
        return self.config['is_login']

    @property
    def uid(self):
        return self.config['uid']

    @set_referer(urls.COMPOSE_REFERER_BASE)
    def send_weibo(self, text: str, image_paths: Optional[Iterable[PathLike]] = None):
        """发送微博

        Args:
            text (str): 正文内容
            image_paths (Optional[Iterable[PathLike]], optional): 图片的路径. Defaults to None.

        Returns:
            返回的json文件。
        """
        data = {
            'content': text,
            'st': self.st,
            # '_spr':
        }

        if not image_paths is None:
            uploaded_image_ids = []
            for image_path in image_paths:
                uploaded_image_ids.append(self.upload_image(image_path)['pic_id'])
                self.session.headers['referer'] = encode_compose_refer(
                    uploaded_image_ids)
            data["picId"] = ','.join(uploaded_image_ids)

        # TODO: 'visible'
        response = self.session.post(urls.SEND_WEIBO, data=data)
        response.raise_for_status()
        return response.json()

    @set_referer(urls.COMPOSE_REFERER_BASE, override=False)
    def upload_image(self, image_path: str):
        """上传图片到微博图床。通常不用手动调用此方法。

        Args:
            image_path (str): 图片路径

        Returns:
            带有以下字段的json返回值
            bmiddle_pic: "http://wx3.sinaimg.cn/bmiddle/{pic_id}.jpg"
            original_pic: "http://wx3.sinaimg.cn/large/{pic_id}.jpg"
            pic_id: "{pic_id}"
            thumbnail_pic: "http://wx3.sinaimg.cn/thumbnail/{pic_id}.jpg"
        """
        image_path = Path(image_path)

        response = self.session.post(
            urls.UPLOAD_IMAGE,
            data={
                'type': 'json',
                'st': self.st,
                # TODO _spr: screen:1536x864
            },
            files={
                'pic': (
                    image_path.name,
                    image_path.open('rb'),
                    'image/jpeg'
                )},
        )
        response.raise_for_status()
        return response.json()
