# -*- coding: utf-8 -*-

'''
'''

import asyncio
import os
import queue
import tempfile
import time

from .down import AsyncDownloader
from .util import logger, merge_files


class M3U8File(object):
    '''
    '''

    def __init__(self, file_path):
        self._file_path = file_path
        self._m3u8_list = []
        self._ts_list = []
        self._sequence = 0
        self.parse()
    
    def parse(self):
        with open(self._file_path) as fp:
            text = fp.read()
            index = 0
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line[0] == '#':
                    if line[1:].startswith('EXT-X-MEDIA-SEQUENCE:'):
                        self._sequence = int(line[22:])
                    continue

                if line.endswith('.m3u8'):
                    self._m3u8_list.append(line)
                elif line.endswith('.ts'):
                    self._ts_list.append(line)

    @property
    def sequence(self):
        return self._sequence

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

    def __init__(self, url, save_path, concurrent=None, timeout=None, try_count=None):
        self._url = url
        self._save_path = save_path
        self._cache_path = 'cache'
        if not os.path.exists(self._cache_path):
            os.mkdir(self._cache_path)
        self._downloader = AsyncDownloader(timeout, try_count)
        self._down_queue = queue.Queue()
        self._running = True
        self._recording = True
        self._running_tasks = 0
        self._ts_list = []
        self._video_count = 0
        self._last_sequence = 0
        self.start_task(self.download_task())
        self.max_concurrent = concurrent or self.__class__.max_concurrent
    
    def gen_url(self, prev_url, url):
        if url.startswith('http:') or url.startswith('htts:'):
            return url
        elif url[0] != '/':
            return prev_url[:prev_url.rfind('/') + 1] + url 
        else:
            return prev_url[:prev_url.find('/', 9)] + url

    def start_task(self, coroutine, delay=0):
        logger.debug('[%s] Start task %s' % (self.__class__.__name__, coroutine.__name__))
        async def _wrap():
            if delay:
                await asyncio.sleep(delay)
            try:
                await coroutine
            except GeneratorExit:
                logger.info('[%s] Task %s exit' % (self.__class__.__name__, coroutine.__name__))
            except:
                import traceback
                traceback.print_exc()
                logger.error('[%s] Task %s exit unexpectly' % (self.__class__.__name__, coroutine.__name__))
                self._running = False

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
        #self._running_tasks += 1
        save_path = tempfile.mkstemp('.m3u8')[1]
        await self._downloader.download(url, save_path)
        mf = M3U8File(save_path)
        for it in mf.m3u8_list:
            new_url = self.gen_url(url, it)
            await self.download_m3u8(new_url)
        index = mf.sequence - self._last_sequence
        for i, it in enumerate(mf.ts_list):
            if mf.sequence and i < len(mf.ts_list) - index:
                continue
            new_url = self.gen_url(url, it)
            self._down_queue.put(new_url)
            self._video_count += 1
        if mf.sequence and self._recording:
            self.start_task(self.download_m3u8(url), 10)
        self._last_sequence = mf.sequence
        #self._running_tasks -= 1

    async def start(self, record_time=0):
        try:
            await self.download_m3u8(self._url)
        except:
            import traceback
            traceback.print_exc()

        print('Found %d video files.' % self._video_count)
        await asyncio.sleep(0.5)
        result = False
        if self._video_count:
            print('0/%d' % self._video_count, end='')
            index = 0
            
            time0 = time.time()
            while True:
                if self._recording and record_time and time.time() - time0 >= record_time:
                    self._recording = False

                if not self._running:
                    return False
                print('\rDownloding %d/%d %s' % (len(self._ts_list) - self._running_tasks, self._video_count, '.' * (index % 3 + 1) + '   '), end='')
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
