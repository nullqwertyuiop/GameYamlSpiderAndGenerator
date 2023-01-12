if __name__ == "__main__":
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import itertools
from contextlib import suppress
from json import loads
from re import match, sub
from typing import AnyStr, List

from bs4 import BeautifulSoup
from html2text import html2text
from langcodes import find

from gameyamlspiderandgenerator.util.plugin_manager import load_plugins
from gameyamlspiderandgenerator.util.setting import get_config
from gameyamlspiderandgenerator.util.spider import get_text

setting = get_config()


class Search:
    @staticmethod
    def verify(url: str):
        return match(r"https://.+\.itch\.io/.+", url) is not None

    def __init__(self, link: AnyStr) -> None:
        self.data_html = get_text(link)
        self.soup = BeautifulSoup(self.data_html, "html.parser")
        self.data = [
            ii
            for ii in [
                loads(i.text)
                for i in self.soup.find_all(
                    "script", attrs={"type": "application/ld+json"}
                )
            ]
            if "name" in ii
        ][0]
        self.more_info = self.get_more_info()
        self.tag = self.get_tag()

    def get_thumbnail(self):
        return self.soup.select_one("#header > img").attrs["src"]

    def get_brief_desc(self):
        return (
            self.data["aggregateRating"]["description"]
            if "description" in self.data["aggregateRating"]
            else None
        )

    def get_name(self):
        return self.data["name"]

    def get_screenshots(self):
        return [
            i.attrs["src"]
            for i in self.soup.find_all("img", attrs={"class": "screenshot"})
        ]

    def get_desc(self):
        return html2text(
            str(self.soup.select_one("div.formatted_description.user_formatted")),
            bodywidth=0,
        ).strip()

    def get_platforms(self):
        repl = {
            "Windows": "windows",
            "macOS": "macos",
            "Linux": "linux",
            "Android": "android",
            "HTML5": "web",
            "iOS": "ios",
        }
        platforms = self.more_info["Platforms"][0].split(",")
        return [repl[i.strip()] for i in platforms]

    def get_authors(self) -> List[dict]:
        temp = self.more_info["Author"]
        return [{"name": i, "role": "developer"} for i in temp]

    def get_tag(self) -> List[str]:
        temp = self.more_info["Genre"] if "Genre" in self.more_info else ""
        temp1 = self.more_info["Made with"] if "Made with" in self.more_info else ""
        temp2 = self.more_info["Tags"]
        return [i.strip() for i in (temp2 + temp1 + temp)]

    def get_misc_tag(self):
        repl = {
            "3D": "3d",
            "Pixel Art": "pixel-art",
            "free": "freeware",
            "Multiplayer": "multiplayer",
            "Co-op": "co-op",
            "PvP": "pvp",
            "Ren'Py": "engine-renpy",
            "Unity": "engine-unity",
            "RPG Maker": "engine-rpg-maker",
            "Godot": "engine-godot",
            "ue4": "engine-ue4",
            "unreal - engine - 4": "engine-ue4",
            "TyranoBuilder": "engine-tyranobuilder",
            "Flash": "adobe-flash",
            "t-series": "multiple-series",
            "Multiple Endings": "multiple-endings",
        }

        ret = []
        for i, value in repl.items():
            ret.extend(value for ii in self.tag if i in ii)
        return list(set(ret))

    def get_lang(self) -> List[str]:
        temp = self.more_info["Languages"]
        return list({find(i).language for i in temp})

    def get_link(self) -> List[dict]:
        link = [i.attrs["href"] for i in self.soup.select("a[href]")]
        fgi_dict = [
            {
                "match": "^https://www.youtube.com/@?([^/]+)/?",
                "prefix": ".youtube",
                "replace": "youtube:@\\g<1>",
            },
            {
                "match": "^https://www.youtube.com/channel/(.+[^/])",
                "prefix": ".youtube",
                "replace": "youtube:\\g<1>",
            },
            {
                "match": "^https://twitter.com/(.{1,})",
                "prefix": ".twitter",
                "replace": "twitter:\\g<1>",
            },
            {
                "match": "^https://www.patreon.com/(.+)",
                "prefix": ".patreon",
                "replace": "patreon:\\g<1>",
            },
            {
                "match": "^https://discord.gg/(.+)",
                "prefix": ".discord",
                "replace": "discord:\\g<1>",
            },
            {
                "match": "https://www.facebook.com/(.+)/",
                "prefix": ".facebook",
                "replace": "facebook:\\g<1>",
            },
        ]
        data = list(list(set(link)))
        return [
            {"name": p["prefix"], "uri": sub(p["match"], p["replace"], i)}
            for i, p in itertools.product(data, fgi_dict)
            if match(p["match"], i) is not None
        ]

    def get_more_info(self):
        d = {}
        for i in range(1, 18):
            with suppress(Exception):
                cache = self.soup.select_one(
                    f"div.info_panel_wrapper > div > table > tbody > tr:nth-child({str(i)})"
                )
                temp = [i.get_text() for i in list(cache.children)]
                d[temp[0]] = temp[1:][0].split(",")
        return d

    def __load_hook(self, data: dict):
        self.pkg = load_plugins()
        temp = data
        for _ in self.pkg["hook"]:
            temp = self.pkg["hook"].Search(self.get_name()).setup(temp)
        return temp


if __name__ == "__main__":
    obj = Search(link="https://fymm-game.itch.io/ddp")
    print(obj.get_thumbnail())
    print(obj.get_desc())
    print(obj.get_name())
    print(obj.get_screenshots())
    print(obj.get_brief_desc())
    print(obj.get_platforms())
    print(obj.get_authors())
    print(obj.get_lang())
    print(obj.get_link())
    print(obj.get_misc_tag())
