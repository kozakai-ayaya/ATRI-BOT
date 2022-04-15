import contextlib
import datetime
from email import contentmanager

from io import IOBase
from os import PathLike
from pathlib import Path
from typing import Iterable, List, Optional, Union

import requests

from ..utils import json_response, set_referer

from ..errors import AuthException, UnexpectedResponseException
from . import urls
from .base import WeiboAPIBase, WeiboAuth, WeiboVisible

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

SPR = 'screen:400x629'


class WeiboH5API(WeiboAPIBase):
    def __init__(self):
        self.session = requests.Session()

        self._config = None
        self._config_update_time = None

    @staticmethod
    def cookies_key_to_domain(key):
        return '.m.weibo.cn' if key == 'XSRF-TOKEN' else '.weibo.cn'

    def init_session(self, timeout: int = 10, proxies: dict[str, str] = None):
        self.session.headers.update(DEAFULT_HEADER)
        self.session.auth = WeiboAuth(self)
        super().init_session(timeout, proxies)
        try:
            self.config
        except UnexpectedResponseException as e:
            raise AuthException() from e

    @property
    def config(self):
        """获取登录信息，更新xsrf token，通常没有必要读取这个字段，可以直接使用is_login，st，uid字段。
        """
        if self._config and self._config_update_time - datetime.datetime.now() < datetime.timedelta(minutes=5):
            return self._config
        self._config = self._get_config()
        self._config_update_time = datetime.datetime.now()
        return self._config

    @set_referer(urls.BASE_URL)
    @json_response
    def _get_config(self):
        return self.session.get(urls.CONFIG)

    @set_referer(urls.COMPOSE_REFERER_BASE)
    @json_response
    def send_weibo(self,
                   text: str,
                   image_paths: Optional[Union[str, PathLike, IOBase]] = None,
                   visible: WeiboVisible = WeiboVisible.EVERYONE
                   ):
        """发送微博

        Args:
            text (str): 正文内容
            image_paths (Optional[Union[str, PathLike, IOBase]], optional): 图片的路径. Defaults to None.

        Returns:
            返回的json文件。
        """
        data = {
            'content': text,
            'st': self.config['st'],
            '_spr': SPR
        }
        if visible != WeiboVisible.EVERYONE:
            data['visible'] = visible.value

        if not image_paths is None:
            uploaded_image_ids = []
            for image_path in image_paths:
                uploaded_image_ids.append(
                    self.upload_image(image_path)['pic_id'])
                self.session.headers['referer'] = encode_compose_refer(
                    uploaded_image_ids)
            data["picId"] = ','.join(uploaded_image_ids)

        return self.session.post(urls.SEND_WEIBO, data=data)

    # handle referer in post method
    @json_response
    def delete_weibo(self, weibo_id: Union[str, int]):
        if isinstance(weibo_id, int):
            weibo_id = str(weibo_id)
        data = {
            'mid': weibo_id,
            'st': self.st,
            '_spr': SPR
        }
        return self.session.post(urls.DELETE_WEIBO, data=data, headers={'referer': f'{urls.BASE_URL}detail/{weibo_id}'})

    @set_referer(urls.COMPOSE_REFERER_BASE, override=False)
    @json_response
    def upload_image(self, image_path_or_stream: Union[str, PathLike, IOBase]):
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
        if isinstance(image_path_or_stream, (str, PathLike)):
            image_path = Path(image_path_or_stream)
            image_name = image_path.name
            image_stream = image_path.open('rb')
        elif isinstance(image_path_or_stream, IOBase):
            image_name = 'image_stream'
            image_stream = image_path_or_stream
        else:
            raise TypeError(f'unknown input type {type(image_stream)}')
        with contextlib.closing(image_stream) as fp:
            response = self.session.post(
                urls.UPLOAD_IMAGE,
                data={
                    'type': 'json',
                    'st': self.config['st'],
                    '_spr': SPR
                },
                files={
                    'pic': (
                        image_name,
                        fp,
                        'image/jpeg'
                    )},
            )
        return response
