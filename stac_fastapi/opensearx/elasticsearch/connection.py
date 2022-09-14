import os

import aiohttp
from elasticsearch import AIOHttpConnection


class ProxyAIOHttpConnection(AIOHttpConnection):
    """
    wrapper class to allow the use of a socks proxy

    Highly specific to elasticsearch-py==7.17.x, so there will have to be a rewrite once
    the database and elasticsearch-py is upgraded to 8.x

    Ideally, though, this could be upstreamed to `elasticsearch`
    """

    async def _create_aiohttp_session(self):
        """Creates an aiohttp.ClientSession(). This is delayed until
        the first call to perform_request() so that AsyncTransport has
        a chance to set AIOHttpConnection.loop
        """
        from aiohttp_socks import ProxyConnector
        from elasticsearch._async.http_aiohttp import ESClientResponse, get_running_loop

        if self.loop is None:
            self.loop = get_running_loop()

        proxy_url = os.environ.get("https_proxy") or os.environ.get("http_proxy")
        connector = ProxyConnector.from_url(
            proxy_url,
            limit=self._limit,
            use_dns_cache=True,
            enable_cleanup_closed=True,
            ssl=self._ssl_context,
        )

        self.session = aiohttp.ClientSession(
            headers=self.headers,
            skip_auto_headers=("accept", "accept-encoding", "user-agent"),
            auto_decompress=True,
            loop=self.loop,
            cookie_jar=aiohttp.DummyCookieJar(),
            response_class=ESClientResponse,
            connector=connector,
        )
