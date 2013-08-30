#!/usr/bin/python
__author__ = 'Alexander Ponomarev'

import msgpack
import socket
from tornado.httpclient import AsyncHTTPClient, HTTPResponse, HTTPRequest, HTTPError
from cocaine.worker import Worker
from cocaine.logging import Logger
from cocaine.futures import chain

class UrlFetcher():
    def __init__(self, io_loop):
        self.io_loop = io_loop
        self.http_client = AsyncHTTPClient()
        self.logger = Logger()

    @chain.source
    def on_get_request(self, request, response):
        request_data_packed = yield request.read()
        request_data = msgpack.unpackb(request_data_packed)

        url = request_data[0]
        try:
            http_request = HTTPRequest(url)

            http_response = yield self.http_client.fetch(http_request)
            response.write( (True, http_response.body, http_response.code, http_response.headers,) )
            http_response.headers.items()
            response.close()
        except HTTPError as e:
            self.logger.info("Error ({0}) occured while downloading {1}".format(e.message, url))
            response.write( (False, '', e.code, {},) )
            response.close()
        except socket.gaierror as e:
            self.logger.info("Error ({0}) occured while downloading {1}".format(e.message, url))
            response.write( (False, '', e.errno, {},) )
            response.close()
        except Exception as e:
            self.logger.error("Unhandled error ({0}) occured while downloading {1}, report about this problem "
                              "to httpclient service developers".format(e.message, url))
            response.write( (False, '', 0, {},) )
            response.close()


def main():
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    worker = Worker()
    urlfetcher = UrlFetcher(io_loop = worker.loop)
    worker.on('get', urlfetcher.on_get_request)
    worker.run()

if __name__ == '__main__':
    main()