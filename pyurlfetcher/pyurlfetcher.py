#!/usr/bin/python
__author__ = 'Alexander Ponomarev'

import msgpack
import socket
from tornado.httpclient import AsyncHTTPClient, HTTPResponse, HTTPRequest, HTTPError
from tornado.httputil import HTTPHeaders
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
        constants = request_consts[method]

        url = request[constants.URL]
        timeout = request[constants.TIMEOUT]
        try:
            http_request = HTTPRequest(url=url, method=method)
            http_request.request_timeout = float(timeout)/1000

            if method == 'POST':
                http_request.body = request[constants.BODY]

            #adds cookies to request
            params_num = len(request)
            if constants.COOKIES <= params_num - 1:
                cookies = request[constants.COOKIES]
                for name, value in cookies.iteritems():
                    http_request.headers.add('Cookie', '{0}={1}'.format(name, value))

            #adds headers to request
            if constants.HEADERS <= params_num - 1:
                for name, values_list in request[constants.HEADERS].iteritems():
                    for value in values_list:
                        http_request.headers.add(name, value)

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
            self.logger.error("Unhandled error ({0}) occured while downloading {1}, report about this problem "
                              "to httpclient service developers".format(e.message, url))
            response.write((False, '', 0, {},))
            response.close()

    @chain.source
    def on_get_request(self, request, response):
        request_data_packed = yield request.read()
        request_data = msgpack.unpackb(request_data_packed)

        yield self.perform_request(request_data, response, 'GET')

    @chain.source
    def on_post_request(self, request, response):
        request_data_packed = yield request.read()
        request_data = msgpack.unpackb(request_data_packed)

        yield self.perform_request(request_data, response, 'POST')

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
    worker.run()


if __name__ == '__main__':
    main()