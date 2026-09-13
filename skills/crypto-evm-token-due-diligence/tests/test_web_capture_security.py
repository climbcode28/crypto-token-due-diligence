"""Offline public-network boundaries for anonymous research captures."""
import http.client
import io
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import web_capture as web


class PublicCaptureTests(unittest.TestCase):
    def test_private_urls_never_reach_transport_or_save_body(self):
        urls = ['http://localhost/', 'https://localhost./', 'https://host.local/',
                'http://host.internal/', 'http://127.0.0.1/', 'http://10.1.2.3/',
                'http://169.254.169.254/latest/meta-data/', 'https://[::1]/',
                'https://[fc00::1]/', 'http://224.0.0.1/']
        class UnexpectedOpener:
            def open(self, *args, **kwargs):
                raise AssertionError('private destination reached HTTP transport')
        with tempfile.TemporaryDirectory() as directory:
            for i, url in enumerate(urls):
                with self.subTest(url=url):
                    row = web.capture_one({'id': str(i), 'url': url}, Path(directory), opener=UnexpectedOpener())
                    self.assertEqual(row['failure_category'], 'refused_private_url')
                    self.assertEqual(row['requests_used'], 0)
                    self.assertIsNone(row['raw'])
            self.assertFalse(list(Path(directory).glob('*.raw')))

    def test_redirect_to_private_network_is_not_followed(self):
        class RedirectOpener:
            def __init__(self): self.urls = []
            def open(self, request, timeout=None):
                self.urls.append(request.full_url)
                raise urllib.error.HTTPError(request.full_url, 302, 'redirect',
                                             {'Location': 'http://169.254.169.254/latest/meta-data/'}, io.BytesIO())
        opener = RedirectOpener()
        with tempfile.TemporaryDirectory() as directory:
            row = web.capture_one({'id': 'redirect', 'url': 'https://example.org/'}, Path(directory), opener=opener)
            self.assertEqual(opener.urls, ['https://example.org/'])
            self.assertEqual(row['failure_category'], 'refused_private_url')
            self.assertEqual(row['requests_used'], 1)
            self.assertIsNone(row['raw'])

    def test_dns_names_resolving_to_private_peers_send_no_http_data(self):
        class Socket:
            def __init__(self, peer): self.peer, self.sent, self.closed = peer, [], False
            def getpeername(self): return (self.peer, 443)
            def sendall(self, data): self.sent.append(data)
            def close(self): self.closed = True
        for connection, base in [(web.PublicHTTPConnection, http.client.HTTPConnection),
                                 (web.PublicHTTPSConnection, http.client.HTTPSConnection)]:
            for peer in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '::ffff:127.0.0.1']:
                with self.subTest(connection=connection.__name__, peer=peer):
                    sock = Socket(peer)
                    def connect(instance): instance.sock = sock
                    with patch.object(base, 'connect', connect):
                        conn = connection('public-looking.example.org')
                        with self.assertRaises(web.PrivateDestination): conn.request('GET', '/')
                    self.assertEqual(sock.sent, [])
                    self.assertTrue(sock.closed)
            sock = Socket('8.8.8.8')
            with patch.object(base, 'connect', lambda instance: setattr(instance, 'sock', sock)):
                conn = connection('example.org')
                try: conn.request('GET', '/')
                finally: conn.close()
            self.assertTrue(sock.sent, 'public connected peers should remain usable')

    def test_environment_proxies_are_not_loaded(self):
        with patch('urllib.request.getproxies', side_effect=AssertionError('inherited proxy lookup')):
            opener = web.public_opener()
        self.assertTrue(any(isinstance(h, web.PublicHTTPHandler) for h in opener.handlers))
        self.assertTrue(any(isinstance(h, web.PublicHTTPSHandler) for h in opener.handlers))
        self.assertFalse(any(isinstance(h, urllib.request.HTTPCookieProcessor) for h in opener.handlers))

    def test_malformed_ports_and_controls_are_refused(self):
        for url in ['https://example.org:0/', 'http://example.org:65536/',
                    'https://example.org/\r\nHeader: value', ' https://example.org/']:
            with self.subTest(url=url), self.assertRaises(ValueError): web.clean_url(url)
        for url in ['https://example.org/docs', 'http://example.org/', 'https://8.8.8.8/']:
            self.assertEqual(web.clean_url(url), url)


if __name__ == '__main__':
    unittest.main()
