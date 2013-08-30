#!/usr/bin/python
__author__ = 'Alexander Ponomarev'

import msgpack
import socket
from tornado.httpclient import AsyncHTTPClient, HTTPResponse, HTTPRequest, HTTPError
from tornado.httputil import HTTPHeaders
from cocaine.worker import Worker
from cocaine.logging import Logger
from cocaine.futures import chain


class RequestConst:
    URL = 0
    TIMEOUT = 1
    COOKIES = 2
    HEADERS = 3
    FOLLOW_REDIRECTS = 4


class UrlFetcher():
    def __init__(self, io_loop):
        self.io_loop = io_loop
        self.http_client = AsyncHTTPClient()
        self.logger = Logger()

    def on_get_request(self, request, response):
        request_data_packed = yield request.read()
        request_data = msgpack.unpackb(request_data_packed)

        self.logger.info("request is {0}".format(str(request_data)))

        url = request_data[RequestConst.URL]
        try:
            http_request = HTTPRequest(url)

            headers = HTTPHeaders()

            if RequestConst.COOKIES in request_data:
                cookies = request_data[RequestConst.COOKIES]
                for name, value in cookies:
                    headers.add('Cookie', '{0}={1}'.format(name, value))

            if RequestConst.HEADERS in request_data:
                for name, values_list in request_data[RequestConst.HEADERS]:
                    for value in values_list:
                        headers.add(name, value)

            http_response = yield self.http_client.fetch(http_request)

            response_headers = {}
            for header_tuple in http_response.headers.items():
                name = header_tuple[0]
                value = header_tuple[1]
                if not name in response_headers:
                    response_headers[name] = []

                response_headers[name].append(value)

            response.write((True, http_response.body, http_response.code, response_headers,))

            response.close()
            self.logger.info("{0} has been successfuly downloaded".format(url))
        except HTTPError as e:
            self.logger.info("Error ({0}) occured while downloading {1}".format(e.message, url))
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


def main():
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    worker = Worker()
    urlfetcher = UrlFetcher(io_loop=worker.loop)
    worker.on('get', urlfetcher.on_get_request)
    worker.run()


if __name__ == '__main__':
    main()