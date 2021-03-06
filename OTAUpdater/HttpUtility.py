import usocket
import machine
import time
import os
import network
import settings
from src.OTAUpdater.uping import ping
import logging

sta_if = network.WLAN(network.STA_IF)
def connected_to_network(ssid=settings.WIFI_SSID, password=settings.WIFI_PASSWORD, timeout=settings.WIFI_TIMEOUT, restart=True):
    global sta_if
    timeout = timeout
    i = 0
    while not sta_if.isconnected():
        sta_if.active(True)
        sta_if.connect(ssid, password)
        time.sleep(1)
        if i == timeout:
            logging.info('connecting {0}'.format(i))
            if restart:
                machine.reset()
            else:
                return False
    try:
        snd, recv = ping('google.com')
        if recv < 1:
            raise Exception("No Internet")
        return True
    except Exception as e:
        if restart:
            machine.reset()
        else:
            logging.error(str(e))
            return False

class Response:

    def __init__(self, f):
        self.raw = f
        self.encoding = 'utf-8'
        self._cached = None
        self.chunk_size = 2048

    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None
        self._cached = None

    def content_chunked(self):
        try:
            data = self.raw.read(self.chunk_size)
            while data:
                logging.debug('yielding data: {0}'.format(data))
                yield data
                data = self.raw.read(self.chunk_size)
        finally:
            self.raw.close()
            self.raw = None

    @property
    def content(self):
        if self._cached is None:
            try:
                self._cached = self.raw.read()
            finally:
                self.raw.close()
                self.raw = None
        return self._cached

    @property
    def text(self):
        return str(self.content, self.encoding)
#        for chunk in self.content_chunked():
#            yield str(chunk, self.encoding)

    def json(self):
        import ujson
        return ujson.loads(self.content)


class HttpClient:

    def __init__(self, headers={}):
        self._headers = headers

    def request(self, method, url, data=None, json=None, headers={}, stream=None):
        def _write_headers(sock, _headers):
            for k in _headers:
                sock.write(b'{}: {}\r\n'.format(k, _headers[k]))

        try:
            proto, dummy, host, path = url.split('/', 3)
        except ValueError:
            proto, dummy, host = url.split('/', 2)
            path = ''
        if proto == 'http:':
            port = 80
        elif proto == 'https:':
            import ussl
            port = 443
        else:
            raise ValueError('Unsupported protocol: ' + proto)

        if ':' in host:
            host, port = host.split(':', 1)
            port = int(port)

        logging.info('addrinfo: {0} - {1}'.format(host, port))
        ai = False
        c = 0
        while not ai:
            try:
                ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
            except OSError as e:
                c += 1
                logging.info('OSError -- in HttpUtility')
                logging.info('{0} - {1}'.format(host, port))
                logging.error(str(e))
                ai = False
                connected_to_network(settings.WIFI_SSID, settings.WIFI_PASSWORD, settings.WIFI_TIMEOUT, restart=False)
                if c > 10:
                    machine.reset()
        try:
            ai = ai[0]

            s = usocket.socket(ai[0], ai[1])
            s.settimeout(50)
        except:
            logging.info("No internet...")
            logging.info("Restart please...")
            time.sleep(5)
            machine.reset()
        try:
            s.connect(ai[-1])
            if proto == 'https:':
                s = ussl.wrap_socket(s, server_hostname=host)
            s.write(b'%s /%s HTTP/1.0\r\n' % (method, path))
            if not 'Host' in headers:
                s.write(b'Host: %s\r\n' % host)
            # Iterate over keys to avoid tuple alloc
            _write_headers(s, self._headers)
            _write_headers(s, headers)

            # add user agent
            s.write('User-Agent')
            s.write(b': ')
            s.write('MicroPython OTAUpdater')
            s.write(b'\r\n')
            if json is not None:
                assert data is None
                import ujson
                data = ujson.dumps(json)
                s.write(b'Content-Type: application/json\r\n')
            if data:
                s.write(b'Content-Length: %d\r\n' % len(data))
            s.write(b'\r\n')
            if data:
                s.write(data)

            l = s.readline()
            l = l.split(None, 2)
            logging.info('l:')
            logging.info(l[0])
            logging.info(l[1])
            status = int(l[1])
            reason = ''
            if len(l) > 2:
                reason = l[2].rstrip()
            while True:
                l = s.readline()
                if not l or l == b'\r\n':
                    break
                if l.startswith(b'Transfer-Encoding:'):
                    if b'chunked' in l:
                        logging.error('ERROR in HttpUtility -> ValueError')
                        raise ValueError('Unsupported ' + l)
                elif l.startswith(b'Location:') and not 200 <= status <= 299:
                    logging.error('ERROR in HttpUtility -> Unsupported')
                    raise NotImplementedError('Redirects not yet supported')
        except OSError:
            s.close()
            raise

        resp = Response(s)
        resp.status_code = status
        resp.reason = reason
        return resp

    def head(self, url, **kw):
        return self.request('HEAD', url, **kw)

    def get(self, url, **kw):
        return self.request('GET', url, **kw)

    def post(self, url, **kw):
        return self.request('POST', url, **kw)

    def put(self, url, **kw):
        return self.request('PUT', url, **kw)

    def patch(self, url, **kw):
        return self.request('PATCH', url, **kw)

    def delete(self, url, **kw):
        return self.request('DELETE', url, **kw)
