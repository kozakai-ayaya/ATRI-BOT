import functools
import logging

import requests

from .errors import UnexpectedResponseException


class HTTPAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, timeout=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout

    def send(self, *args, **kwargs):
        # set timeout default value
        if kwargs['timeout'] is None:
            kwargs['timeout'] = self.timeout
        return super().send(*args, **kwargs)


def prepare_session(session, timeout=None, proxies=None):
    session.mount("http://", HTTPAdapter(timeout=timeout))
    if proxies:
        session.proxies.update(proxies)
        session.trust_env = False


def setup_logger(
    name=None,
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    filepath=None,
) -> logging.Logger:
    """Setups logger: name, level, format etc.
    (From ignite utils)

    Args:
        name (str, optional): new name for the logger. If None, the standard logger is used.
        level (int): logging level, e.g. CRITICAL, ERROR, WARNING, INFO, DEBUG
        format (str): logging format. By default, `%(asctime)s %(name)s %(levelname)s: %(message)s`
        filepath (str, optional): Optional logging file path. If not None, logs are written to the file.

    Returns:
        logging.Logger

    For example, to improve logs readability when training with a trainer and evaluator:

    .. code-block:: python

        from ignite.utils import setup_logger

        trainer = ...
        evaluator = ...

        trainer.logger = setup_logger("trainer")
        evaluator.logger = setup_logger("evaluator")

        trainer.run(data, max_epochs=10)

        # Logs will look like
        # 2020-01-21 12:46:07,356 trainer INFO: Engine run starting with max_epochs=5.
        # 2020-01-21 12:46:07,358 trainer INFO: Epoch[1] Complete. Time taken: 00:5:23
        # 2020-01-21 12:46:07,358 evaluator INFO: Engine run starting with max_epochs=1.
        # 2020-01-21 12:46:07,358 evaluator INFO: Epoch[1] Complete. Time taken: 00:01:02
        # ...

    """
    logger = logging.getLogger(name)

    # don't propagate to ancestors
    # the problem here is to attach handlers to loggers
    # should we provide a default configuration less open ?
    if name is not None:
        logger.propagate = False

    # Remove previous handlers
    if logger.hasHandlers():
        for h in list(logger.handlers):
            logger.removeHandler(h)

    formatter = logging.Formatter(format)

    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if filepath is not None:
        fh = logging.FileHandler(filepath)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def set_referer(url, override=True):
    def wrapper_maker(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self = args[0]
            origin_referer = self.session.headers.get('referer')
            if not override and origin_referer:
                return func(*args, **kwargs)
            self.session.headers['referer'] = url
            try:
                return func(*args, **kwargs)
            finally:
                if origin_referer:
                    self.session.headers['referer'] = origin_referer
                else:
                    self.session.headers.pop('referer')
        return wrapper
    return wrapper_maker


def json_response(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]

        # replace header value of Accept for higher priority of json reponse
        origin_accept = self.session.headers.get('Accept')
        self.session.headers['Accept'] = 'application/json, text/plain, */*'
        
        try:
            response = func(*args, **kwargs)
            response_json = response.json()
        except requests.JSONDecodeError as inner_e:
            raise UnexpectedResponseException(response) from inner_e
        finally:
            self.session.headers['Accept'] = origin_accept or '*/*'

        if response_json.get('ok') is not None and response_json['ok'] != 1:
            raise UnexpectedResponseException(response)
        response_json = response_json.get(
            'data') or response_json.get('msg') or response_json
        return response_json
    return wrapper
