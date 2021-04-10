# -*- coding: utf-8 -*-

"""
"""

import argparse
import asyncio
import logging
import time

from .m3u8 import M3U8Downloader
from .youtube import YouTubeDownloader
from .util import logger


async def download_video(args):
    url = args.url
    save_path = args.save_path
    timeout = args.timeout
    try_count = args.try_count
    if url.startswith("https://www.youtube.com/"):
        downloader = YouTubeDownloader(url, save_path, timeout, try_count)
        await downloader.download()
    else:
        await download_m3u8_video(
            url, save_path, args.concurrency, timeout, try_count, args.record_time
        )


async def download_m3u8_video(
    url, save_path, concurrency, timeout, try_count, record_time
):
    md = M3U8Downloader(url, save_path, concurrency, timeout, try_count)
    time0 = time.time()
    print("Analyzing file list...")
    if await md.start(record_time):
        time_cost = time.time() - time0
        print("File has been saved to %s, total cost %ss" % (save_path, time_cost))


def main():
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("url", help="the url of video, m3u8/youtube")
    parser.add_argument("save_path", help="the path to save m3u8 file")
    parser.add_argument(
        "-c", "--concurrency", type=int, default=5, help="download concurrent"
    )
    parser.add_argument(
        "-v", "--verbose", default=False, help="verbose", action="store_true"
    )
    parser.add_argument("--timeout", type=int, default=0, help="download timeout")
    parser.add_argument("--try-count", type=int, default=5, help="download retry count")
    parser.add_argument(
        "--record-time", type=int, default=0, help="video record seconds"
    )
    args = parser.parse_args()
    if args.verbose:
        print("Verbose logger enabled")
        logger.setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(download_video(args))
    # for task in getattr(asyncio.Task, "all_tasks", asyncio.all_tasks)():
    #     task.cancel()
    loop.close()


if __name__ == "__main__":
    main()
