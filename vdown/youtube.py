# -*- coding: utf-8 -*-

"""youtube video
"""

import json
import os
import urllib.parse
import xml.dom.minidom
import time

import bs4

from .down import AsyncDownloader


class YouTubeDownloader(object):
    root_url = "https://www.youtube.com"

    def __init__(self, url, save_path, timeout=None, try_count=None):
        self._video_id = None
        self._channel = None
        pos = url.find("/watch?v=")
        if pos >= 0:
            self._video_id = url[pos + 9 :]
            if "&" in self._video_id:
                pos = self._video_id.find("&")
                self._video_id = self._video_id[:pos]
        else:
            pos = url.find("/channel/")
            if pos < 0:
                raise ValueError("Invalid youtube video url: %s" % url)
            self._channel = url[pos:].split("/")[2]
        self._save_path = save_path
        self._downloader = AsyncDownloader(timeout or 3600, try_count)

    async def get_video_info(self, video_id):
        url = (
            "%s/get_video_info?video_id=%s&el=embedded&ps=default&eurl=&gl=US&hl=en"
            % (self.root_url, video_id)
        )
        response = await self._downloader.download(url)
        response = response.decode()
        video_info = {}
        for it in response.split("&"):
            key, value = it.split("=", 1)

            if key == "player_response":
                value = urllib.parse.unquote(value)
                video_data = json.loads(value)
                video_details = video_data["videoDetails"]
                streaming_data = video_data["streamingData"]
                video_info["title"] = video_details["title"]
                video_info["videos"] = []
                for stream in streaming_data["formats"]:
                    video_info["videos"].append(
                        {
                            "url": stream["url"],
                            "format": stream["mimeType"],
                            "bitrate": stream["bitrate"],
                            "size": stream.get("contentLength"),
                            "width": stream["width"],
                            "height": stream["height"],
                        }
                    )

                if "captions" in video_data:
                    caption_tracks = video_data["captions"][
                        "playerCaptionsTracklistRenderer"
                    ]["captionTracks"]
                    for it in caption_tracks:
                        video_info["caption_url"] = it["baseUrl"]
                        break
        return video_info

    async def _download(self, video_id, **filters):
        video_info = await self.get_video_info(video_id)
        for video in video_info["videos"]:
            format = filters.get("format")
            if format and format not in video["format"]:
                continue
            width = filters.get("width")
            if width and video["width"] != width:
                continue
            height = filters.get("height")
            if height and video["height"] != height:
                continue
            save_path = self._save_path
            if os.path.isdir(save_path):
                video_format = video["format"]
                ext = video_format.split(";")[0].split("/")[1]
                filename = "%s-%dx%d.%s" % (
                    video_info["title"].replace(":", "-").replace("+", " "),
                    video["width"],
                    video["height"],
                    ext,
                )
                save_path = os.path.join(save_path, filename)
            print("Downloading %s" % video["url"])
            time0 = time.time()
            await self._downloader.download(video["url"], save_path=save_path)
            print("Download complete, cost %.2fs" % (time.time() - time0))

    async def download(self, **filters):
        if self._video_id:
            await self._download(self._video_id)
        elif self._channel:
            async for video in self.get_video_list(self._channel):
                await self._download(video)

    async def get_video_list(self, channel):
        url = "%s/channel/%s/videos" % (self.root_url, channel)
        response = await self._downloader.download(url)
        response = response.decode()
        soup = bs4.BeautifulSoup(response, features="html.parser")

        for script in soup.find_all("script"):
            text = script.string
            if text and "ytInitialData" in text:
                text = text.strip()
                pos = text.find("{")
                try:
                    data = json.loads(text[pos:-1])
                except json.JSONDecodeError:
                    continue

                next_token = None
                next_key = None
                for tab in data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]:
                    if "tabRenderer" in tab and "content" in tab["tabRenderer"]:
                        for content in tab["tabRenderer"]["content"][
                            "sectionListRenderer"
                        ]["contents"]:
                            for item in content["itemSectionRenderer"]["contents"]:
                                for it in item["gridRenderer"]["items"]:
                                    yield it["gridVideoRenderer"]["videoId"]
                                for it in item["gridRenderer"]["continuations"]:
                                    next_token = it["nextContinuationData"][
                                        "continuation"
                                    ]
                                    next_key = it["nextContinuationData"][
                                        "clickTrackingParams"
                                    ]

                while True:
                    url = "%s/browse_ajax?ctoken=%s&continuation=%s&itct=%s" % (
                        self.root_url,
                        next_token,
                        next_token,
                        next_key,
                    )
                    headers = {
                        "x-youtube-client-name": "1",
                        "x-youtube-client-version": "2.20210107.08.00",
                    }
                    response = await self._downloader.download(url, headers=headers)
                    response = response.decode()
                    data = json.loads(response.strip())
                    data = data[1]["response"]["continuationContents"][
                        "gridContinuation"
                    ]
                    for it in data["items"]:
                        yield it["gridVideoRenderer"]["videoId"]
                    if "continuations" not in data:
                        break
                    for it in data["continuations"]:
                        next_token = it["nextContinuationData"]["continuation"]
                        next_key = it["nextContinuationData"]["clickTrackingParams"]

                break
