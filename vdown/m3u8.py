# -*- coding: utf-8 -*-

'''
'''

import asyncio
import os
import queue
import tempfile

from .down import AsyncDownloader
from .util import logger, merge_files


class M3U8File(object):
    '''
    '''

    def __init__(self, file_path):
        self._file_path = file_path
        self._m3u8_list = []
        self._ts_list = []
        self.parse()
    
    def parse(self):
        with open(self._file_path) as fp:
            text = fp.read()
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line[0] == '#':
                    continue

                if line.endswith('.m3u8'):
                    self._m3u8_list.append(line)
                elif line.endswith('.ts'):
                    self._ts_list.append(line)

    @property
    def m3u8_list(self):
        return self._m3u8_list

    @property
    def ts_list(self):
        return self._ts_list


class M3U8Downloader(object):
    '''
    '''
    max_concurrent = 20

    def __init__(self, url, save_path, concurrent=None):
        self._url = url
        self._save_path = save_path
        self._cache_path = 'cache'
        if not os.path.exists(self._cache_path):
            os.mkdir(self._cache_path)
        self._downloader = AsyncDownloader()
        self._down_queue = queue.Queue()
        self._running = True
        self._running_tasks = 0
        self._ts_list = []
        self.start_task(self.download_task())
        self.max_concurrent = concurrent or self.__class__.max_concurrent
    
    def gen_url(self, prev_url, url):
        if url.startswith('http:') or url.startswith('htts:'):
            return url
        elif url[0] != '/':
            return prev_url[:prev_url.rfind('/') + 1] + url 
        else:
            return prev_url[:prev_url.find('/', 9)] + url

    def start_task(self, coroutine):
        logger.debug('[%s] Start task %s' % (self.__class__.__name__, coroutine.__name__))
        async def _wrap():
            try:
                await coroutine
            except GeneratorExit:
                logger.info('[%s] Task %s exit' % (self.__class__.__name__, coroutine.__name__))
            except:
                import traceback
                traceback.print_exc()
                logger.error('[%s] Task %s exit unexpectly' % (self.__class__.__name__, coroutine.__name__))

        asyncio.ensure_future(_wrap())

    async def download_task(self):
        while self._running:
            if self._running_tasks >= self.max_concurrent:
                await asyncio.sleep(0.5)
                continue
            if self._down_queue.empty():
                await asyncio.sleep(0.1)
                continue

            url = self._down_queue.get(False)
            file_name = url.split('/')[-1]
            save_path = os.path.join(self._cache_path, file_name)
            self._ts_list.append(save_path)
            async def download(url, save_path):
                await self._downloader.download(url, save_path)
                self._running_tasks -= 1
            if not os.path.exists(save_path):
                self.start_task(download(url, save_path))
                self._running_tasks += 1
        logger.info('[%s] Download task exit' % self.__class__.__name__)

    async def download_m3u8(self, url):
        self._running_tasks += 1
        save_path = tempfile.mkstemp('.m3u8')[1]
        await self._downloader.download(url, save_path)
        mf = M3U8File(save_path)
        for it in mf.m3u8_list:
            new_url = self.gen_url(url, it)
            await self.download_m3u8(new_url)
        for it in mf.ts_list:
            new_url = self.gen_url(url, it)
            self._down_queue.put(new_url)
        self._running_tasks -= 1

    async def start(self):
        try:
            await self.download_m3u8(self._url)
        except:
            import traceback
            traceback.print_exc()
        video_count = self._down_queue.qsize()
        print('Found %d video files.' % video_count)
        await asyncio.sleep(0.5)
        result = False
        if video_count:
            print('0/%d' % video_count, end='')
            index = 0
            while True:
                print('\r%d Downloding %d/%d %s' % (self._running_tasks, video_count - self._down_queue.qsize(), video_count, '.' * (index % 3 + 1) + '   '), end='')
                if self._running_tasks == 0:
                    break
                await asyncio.sleep(0.5)
                index += 1
        self._running = False
        await asyncio.sleep(0.5)
        
        if self._ts_list:
            print('\nMerge viedeo files...')
            merge_files(self._ts_list, self._save_path)
            result = True
        await self._downloader.close()
        return result
