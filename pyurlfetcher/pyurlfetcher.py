#!/usr/bin/python
__author__ = 'Alexander Ponomarev'

import msgpack
import socket
import traceback
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from cocaine.worker import Worker
from cocaine.logging import Logger
from cocaine.futures import chain


class GetRequestConst:
    URL = 0
    TIMEOUT = 1
    COOKIES = 2
    HEADERS = 3
    FOLLOW_REDIRECTS = 4

class PostRequestConst:
    URL = 0
    BODY = 1
    TIMEOUT = 2
    COOKIES = 3
    HEADERS = 4
    FOLLOW_REDIRECTS = 5

request_consts = {
    'GET' : GetRequestConst,
    'POST' : PostRequestConst
}

class UrlFetcher():
    def __init__(self, io_loop):
        self.io_loop = io_loop
        self.http_client = AsyncHTTPClient()
        self.logger = Logger()

    @chain.source
    def perform_request(self, request, response, method):
        try:
            constants = request_consts[method]

            url = request[constants.URL]
            timeout = request[constants.TIMEOUT]

            http_request = HTTPRequest(url=url, method=method)
            http_request.request_timeout = float(timeout)/1000

            if method == 'POST':
                http_request.body = request[constants.BODY]

            #adds cookies to request
            params_num = len(request)
            if constants.COOKIES <= params_num - 1:
                cookies = request[constants.COOKIES]
                if len(cookies) > 0:
                    list_of_cookies = list('{0}={1}'.format(cookie, value) for cookie, value in cookies.iteritems())
                    cookies_str = '; '.join(list_of_cookies)

                    http_request.headers.add('Cookie', cookies_str)

            #adds headers to request
            if constants.HEADERS <= params_num - 1:
                for name, values_list in request[constants.HEADERS].iteritems():
                    for value in values_list:
                        http_request.headers.add(name, value)

            self.logger.info("Downloading {0}, headers {1}, method {2}".format(url, http_request.headers, method))
            http_response = yield self.http_client.fetch(http_request)

            response_headers = self._get_headers_from_response(http_response)
            response.write((True, http_response.body, http_response.code, response_headers,))

            response.close()
            self.logger.info("{0} has been successfuly downloaded".format(url))
        except HTTPError as e:
            self.logger.info("Error ({0}) occured while downloading {1}".format(e.message, url))

            if e.response is not None:
                http_response = e.response
                response_headers = self._get_headers_from_response(http_response)
                response.write((False, http_response.body, http_response.code, response_headers,))
            else:
                response.write((False, '', e.code, {},))

            response.close()
        except socket.gaierror as e:
            self.logger.info("Error ({0}) occured while downloading {1}".format(e.message, url))
            response.write((False, '', e.errno, {},))
            response.close()
        except Exception as e:
            self.logger.error("Unhandled error ({0}) occured in perform_request, report about this problem "
                          "to httpclient service developers. Method is {1}, stacktrace is: {2}".format(
                                e.message, method, traceback.format_exc()))

            response.write((False, '', 0, {},))
            response.close()

    @chain.source
    def on_get_request(self, request, response):
        try:
            request_data_packed = yield request.read()
            request_data = msgpack.unpackb(request_data_packed)

            yield self.perform_request(request_data, response, 'GET')
        except Exception as e:
            self.logger.error("Unhandled error ({0}) occured in on_get_request, report about this problem "
                              "to httpclient service developers. Stacktrace is: {1}".format(e.message, traceback.format_exc()))
            response.write((False, '', 0, {},))
            response.close()

    @chain.source
    def on_post_request(self, request, response):
        try:
            request_data_packed = yield request.read()
            request_data = msgpack.unpackb(request_data_packed)

            yield self.perform_request(request_data, response, 'POST')
        except Exception as e:
            self.logger.error("Unhandled error ({0}) occured in on_post_request, report about this problem "
                              "to httpclient service developers. Stacktrace is: {1}".format(e.message, traceback.format_exc()))
            response.write((False, '', 0, {},))
            response.close()

    def _get_headers_from_response(self, http_response):
        response_headers = {}
        for header_tuple in http_response.headers.items():
            name = header_tuple[0]
            value = header_tuple[1]
            if not name in response_headers:
                response_headers[name] = []

            response_headers[name].append(value)

        return response_headers

def main():
    worker = Worker()
    urlfetcher = UrlFetcher(io_loop=worker.loop)
    worker.on('get', urlfetcher.on_get_request)
    worker.on('post', urlfetcher.on_post_request)
    worker.run()


if __name__ == '__main__':
    main()