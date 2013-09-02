__author__ = 'Alexander Ponomarev <noname@yandex-team.ru>'

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import msgpack
import json
from tornado.testing import AsyncTestCase, gen
from ..pyurlfetcher import UrlFetcher
from cocaine.testing import gen_test
from tornado.ioloop import IOLoop

class RequestMock(object):
    def __init__(self, url='', method='GET', timeout=5000, cookies=None, headers=None, body='', follow_location=None):
        super(RequestMock, self).__init__()
        self.url = url
        self.method = method
        self.timeout = timeout
        self.cookies = cookies
        self.headers = headers
        self.body = body
        self.follow_location = follow_location

    def read(self):
        request_list = [self.url]
        if self.method == 'POST':
            request_list.append(self.body)
        request_list.append(self.timeout)
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

        url = 'http://httpbin.org/status/404'
        request = RequestMock(url=url)
        response = ResponseMock()
        try:
            urlfetcher.on_get_request(request, response).get()
        except Exception as e:
            self.assertEquals(response.response[0],False)
        response = ResponseMock()

    def test_httpget_wrong_host(self):
        urlfetcher = UrlFetcher(self.ioLoop)

        url = 'http://httpbinbbbbb.org/status/200'
        request = RequestMock(url=url)
        response = ResponseMock()
        try:
            urlfetcher.on_get_request(request, response).get()
        except Exception as e:
            self.assertEquals(response.response[0],False)
        response = ResponseMock()

    def test_httpget(self):
        urlfetcher = UrlFetcher(self.ioLoop)

        url = 'http://httpbin.org/get'
        request = RequestMock(url=url, cookies={'test' : 'testvalue'}, headers={'Cookie':['a=1', 'b=2'], 'Test-Header': ['test-value']})
        response = ResponseMock()
        urlfetcher.on_get_request(request, response).get()
        self.assertEquals(response.response[0],True)
        self.assertGreater(len(response.response[1]), 100)
        self.assertEquals(response.response[2],200)
        self.assertIn('Connection', response.response[3])
        self.assertIn('Content-Type', response.response[3])

        request_json = json.loads(response.response[1])
        self.assertIn('Test-Header', request_json["headers"])
        self.assertEquals(request_json["headers"]['Test-Header'], 'test-value')
        self.assertIn('Cookie', request_json["headers"])

    def test_httppost(self):
        urlfetcher = UrlFetcher(self.ioLoop)

        url = 'http://httpbin.org/post'
        request = RequestMock(url=url, method='POST', body='test_data')
        response = ResponseMock()
        urlfetcher.on_post_request(request, response).get()
        self.assertEquals(response.response[0],True)
        self.assertGreater(len(response.response[1]), 100)
        self.assertEquals(response.response[2],200)
        self.assertIn('Connection', response.response[3])
        self.assertIn('Content-Type', response.response[3])

        request_json = json.loads(response.response[1])
        self.assertEquals(request_json["data"], 'test_data')

if __name__ == '__main__':
    unittest.main()