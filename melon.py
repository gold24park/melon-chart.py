import json
import re
import sys
from datetime import datetime

import requests

_APP_VERSION = "6.5.8.1"
_CP_ID = "AS40"
_USER_AGENT = f"{_CP_ID}; Android 13; {_APP_VERSION}; sdk_gphone64_arm64"
_CHART_API_URL = f"https://m2.melon.com/m6/chart/ent/songChartList.json?cpId={_CP_ID}&cpKey=14LNC3&appVer={_APP_VERSION}"


class MelonChartRequestException(Exception):
    pass


class MelonChartParseException(Exception):
    pass


class ChartEntry:
    """Represents an entry on a chart.
    Attributes:
        title: The title of the track
        artist: The name of the artist.
        image: The URL of the cover image for the track
        lastPos: The track's last position on the previous period.
        rank: The track's current rank position on the chart.
        isNew: Whether the track is new to the chart.
    """

    def __init__(self, title: str, artist: str, image: str, lastPos: int, rank: int, isNew: bool):
        self.title = title
        self.artist = artist
        self.image = image
        self.lastPos = lastPos
        self.rank = rank
        self.isNew = isNew

    def __repr__(self):
        return "{}.{}(title={!r}, artist={!r})".format(
            self.__class__.__module__, self.__class__.__name__, self.title, self.artist
        )

    def __str__(self):
        """Returns a string of the form 'TITLE by ARTIST'."""
        if self.title:
            s = u"'%s' by %s" % (self.title, self.artist)
        else:
            s = u"%s" % self.artist

        if sys.version_info.major < 3:
            return s.encode(getattr(sys.stdout, "encoding", "") or "utf8")
        else:
            return s

    def json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4, ensure_ascii=False)


class ChartData:
    """Represents a particular Bugs chart by a particular period.
    Attributes:
        name: The chart name
        date: The chart date
        imageSize: The size of cover image for the track. (default: 256)
        fetch: A boolean value that indicates whether to retrieve the chart data immediately. If set to `False`, you can fetch the data later using the `fetchEntries()` method.
    """
    def __init__(self, imageSize: int = 256, fetch: bool = True):
        self.imageSize = imageSize
        self.entries = []

        if fetch:
            self.fetchEntries()

    def __getitem__(self, key):
        return self.entries[key]

    def __len__(self):
        return len(self.entries)

    def json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4, ensure_ascii=False)

    def fetchEntries(self):
        headers = {
            "User-Agent": _USER_AGENT
        }

        res = requests.get(
            _CHART_API_URL,
            headers=headers
        )

        if res.status_code != 200:
            message = f"Request is invalid. response status code={res.status_code}"
            raise MelonChartRequestException(message)

        data = res.json()
        self._parseEntries(data)

    def _parseEntries(self, data):
        try:
            self.name = data["response"]['PAGE']
            self.date = self._parseDate(f"{data['response']['RANKDAY']} {data['response']['RANKHOUR']}")
            for item in data['response']['SONGLIST']:
                entry = ChartEntry(
                    title=item['SONGNAME'],
                    artist=item['ARTISTLIST'][0]['ARTISTNAME'],
                    image=self._getResizedImage(item['ALBUMIMG']),
                    rank=int(item["CURRANK"]),
                    lastPos=int(item["PASTRANK"]),
                    isNew=item["RANKTYPE"] == "NEW"
                )
                self.entries.append(entry)
        except Exception as e:
            raise MelonChartParseException(e)

    def _parseDate(self, formatted):
        date_format = "%Y.%m.%d %H:%M"
        return datetime.strptime(formatted, date_format)

    def _getResizedImage(self, url):
        pattern = r"resize/\d+"
        return re.sub(pattern, f"resize/{self.imageSize}", url)
