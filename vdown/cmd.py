# -*- coding: utf-8 -*-

'''
'''

import argparse
import asyncio
import time

from .m3u8 import M3U8Downloader

async def download_m3u8_video(url, save_path, concurrent):
    md = M3U8Downloader(url, save_path, concurrent)
    time0 = time.time()
    print('Analyzing file list...')
    if await md.start():
        time_cost = time.time() - time0
        print('File has been saved to %s, total cost %ss' % (save_path, time_cost))

def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('url', help='the url of m3u8 file')
    parser.add_argument('save_path', help='the path to save m3u8 file')
    parser.add_argument('-c', '--concurrent', dest='concurrent', type=int, default=5, help='download concurrent')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(download_m3u8_video(args.url, args.save_path, args.concurrent))
    for task in asyncio.Task.all_tasks():
        print(task)
        task.cancel()
    loop.close()

if __name__ == '__main__':
    main()