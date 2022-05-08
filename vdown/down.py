# -*- coding: utf-8 -*-

"""Async HTTP Downloader
"""

import asyncio
import os
import ssl

import aiohttp

from .util import logger

ssl._create_default_https_context = ssl._create_unverified_context


class AsyncDownloader(object):
    """async download"""

    try_count = 5
    timeout = 30

    def __init__(self, timeout=None, try_count=None):
        self.timeout = timeout or self.__class__.timeout
        self.try_count = try_count or self.__class__.try_count
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self._session = aiohttp.ClientSession(connector=conn, timeout=timeout)
        self._context = ssl._create_unverified_context()
        self._proxies = {}
        if os.environ.get("http_proxy"):
            self._proxies["http"] = os.environ["http_proxy"]
        if os.environ.get("https_proxy"):
            self._proxies["https"] = os.environ["https_proxy"]

    async def download(self, url, headers=None, save_path=None):
        logger.debug("[%s] Download %s" % (self.__class__.__name__, url))
        headers = headers or {}
        proxy = None
        if url.startswith("http:"):
            proxy = self._proxies.get("http")
        elif url.startswith("https:"):
            proxy = self._proxies.get("https")

        for i in range(self.try_count):
            if i > 0:
                logger.warn(
                    "[%s] Retry to download %s" % (self.__class__.__name__, url)
                )
            try:
                response = await self._session.get(url, headers=headers, proxy=proxy)
                content = await response.read()
            except Exception as e:
                logger.exception(
                    "[%s] Read %s failed: %s" % (self.__class__.__name__, url, e)
                )
                await asyncio.sleep(1)
            else:
                response.raise_for_status()
                break
        else:
            raise RuntimeError("Read %s failed" % url)

        if content.startswith(b"\x89PNG"):
            content = content[212:]
        if save_path:
            with open(save_path, "wb") as fp:
                fp.write(content)
        else:
            return content

    async def close(self):
        await self._session.close()
        self._session = None
