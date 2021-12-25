class BaseError(Exception):
    pass


class UnexpectedResponseException(BaseError):
    def __init__(self, res):
        """
        服务器回复了和预期格式不符的数据
        """
        self.res = res

    def __repr__(self):
        return 'Get an unexpected response when visit url [{res.url}]' \
               'the response body is [{res.text}]'.format(res=self.res)

    __str__ = __repr__
