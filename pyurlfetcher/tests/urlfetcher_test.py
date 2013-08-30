__author__ = 'Alexander Ponomarev <noname@yandex-team.ru>'

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import msgpack
from tornado.testing import AsyncTestCase, gen
from ..pyurlfetcher import UrlFetcher
from cocaine.testing import gen_test
from tornado.ioloop import IOLoop

class RequestMock(object):
    def __init__(self, url='', timeout=5000, cookies=None, headers=None, follow_location=None):
        super(RequestMock, self).__init__()
        self.url = url
        self.timeout = timeout
        self.cookies = cookies
        self.headers = headers
        self.follow_location = follow_location

    def read(self):
        request_list = [self.url, self.timeout]
        if self.cookies: request_list.append(self.cookies)
        if self.headers: request_list.append(self.headers)
        if self.follow_location: request_list.append(self.follow_location)

        meta = msgpack.packb(tuple(request_list))
        return meta

class ResponseMock(object):
    def __init__(self, on_close=None):
        super(ResponseMock, self).__init__()
        self.response = None
        self.on_close = on_close
        self._closed = False

    def write(self, body):
        self.response = body

    def close(self):
        if self.on_close and callable(self.on_close):
            self._closed = True
            self.on_close(self.response)

    @property
    def closed(self):
        return self._closed

class UrlFetcherTestCase(AsyncTestCase):

    ioLoop = IOLoop.instance()

    def test_httpget_not_found(self):
        urlfetcher = UrlFetcher(self.ioLoop)

        url = 'http://yandex.ru/sdfsdfsdfsdf'
        request = RequestMock(url=url)
        response = ResponseMock()
        try:
            urlfetcher.on_get_request(request, response).get()
        except Exception as e:
            self.assertEquals(response.response[0],False)
        response = ResponseMock()

    def test_httpget_wrong_host(self):
        urlfetcher = UrlFetcher(self.ioLoop)

        url = 'http://yandexsdfsdf.ru/sdfsdfsdfsdf'
        request = RequestMock(url=url)
        response = ResponseMock()
        try:
            urlfetcher.on_get_request(request, response).get()
        except Exception as e:
            self.assertEquals(response.response[0],False)
        response = ResponseMock()

    def test_httpget(self):
        urlfetcher = UrlFetcher(self.ioLoop)

        url = 'http://ya.ru'
        request = RequestMock(url=url, cookies={'test' : 'testvalue'}, headers={'Cookie':['a=1', 'b=2'], 'Accept-Language': ['ru-Ru']})
        response = ResponseMock()
        urlfetcher.on_get_request(request, response).get()
        self.assertEquals(response.response[0],True)
        self.assertGreater(len(response.response[1]), 100)
        self.assertEquals(response.response[2],200)
        self.assertIn('Connection', response.response[3])
        self.assertIn('Content-Type', response.response[3])


if __name__ == '__main__':
    unittest.main()