# -*- coding: utf-8 -*-

'''
'''

import asyncio

import aiohttp

from .util import logger


class AsyncDownloader(object):
    '''async download
    '''
    try_count = 5
    timeout = 30

    def __init__(self, timeout=None, try_count=None):
        self.timeout = timeout or self.__class__.timeout
        self.try_count = try_count or self.__class__.try_count
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def download(self, url, save_path):
        logger.debug('[%s] Download %s' % (self.__class__.__name__, url))
        for i in range(self.try_count):
            if i > 0:
                logger.warn('[%s] Retry to download %s' % (self.__class__.__name__, url))
            try:
                response = await self._session.get(url)
                content = await response.read()
            except Exception as e:
                logger.exception('[%s] Read %s failed: %s' % (self.__class__.__name__, url, e))
                await asyncio.sleep(1)
            else:
                response.raise_for_status()
                break
        else:
            raise RuntimeError('Read %s failed' % url)

        with open(save_path, 'wb') as fp:
            fp.write(content)
    
    async def close(self):
        await self._session.close()
        self._session = None
