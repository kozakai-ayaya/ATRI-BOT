import requests

class HTTPAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, timeout=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout

    def send(self, *args, **kwargs):
        # set timeout default value
        if kwargs['timeout'] is None:
           kwargs['timeout'] = self.timeout
        return super().send(*args, **kwargs)

# s = requests.Session()
# s.mount("http://", MyHTTPAdapter(timeout=10))