import os
import coc
from typing import Optional, List
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from dotenv import load_dotenv
from msgspec.json import decode
from msgspec import Struct
from pymongo import UpdateOne, DeleteOne
from datetime import timedelta
from asyncio_throttle import Throttler
from redis import asyncio as aioredis

import redis
import motor.motor_asyncio
import collections
import aiohttp
import asyncio
import pytz


keys = []
utc = pytz.utc
load_dotenv()

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"), maxPoolSize=1000)
looper = client.looper
clan_tags = looper.clan_tags
rankings = client.new_looper.rankings
throttler = Throttler(rate_limit=1000, period=1)

emails = []
passwords = []
#26-29 (30)
for x in range(23,26):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(os.getenv("COC_PASSWORD"))

async def get_keys(emails: list, passwords: list, key_names: str, key_count: int):
    total_keys = []

    for count, email in enumerate(emails):
        _keys = []
        password = passwords[count]

        session = aiohttp.ClientSession()

        body = {"email": email, "password": password}
        resp = await session.post("https://developer.clashofclans.com/api/login", json=body)
        if resp.status == 403:
            raise RuntimeError(
                "Invalid Credentials"
            )

        resp_paylaod = await resp.json()
        ip = json_loads(base64_b64decode(resp_paylaod["temporaryAPIToken"].split(".")[1] + "====").decode("utf-8"))[
            "limits"][1]["cidrs"][0].split("/")[0]

        resp = await session.post("https://developer.clashofclans.com/api/apikey/list")
        keys = (await resp.json())["keys"]
        _keys.extend(key["key"] for key in keys if key["name"] == key_names and ip in key["cidrRanges"])

        for key in (k for k in keys if ip not in k["cidrRanges"]):
            await session.post("https://developer.clashofclans.com/api/apikey/revoke", json={"id": key["id"]})

        print(len(_keys))
        while len(_keys) < key_count:
            data = {
                "name": key_names,
                "description": "Created on {}".format(datetime.now().strftime("%c")),
                "cidrRanges": [ip],
                "scopes": ["clash"],
            }
            resp = await session.post("https://developer.clashofclans.com/api/apikey/create", json=data)
            key = await resp.json()
            _keys.append(key["key"]["key"])

        if len(keys) == 10 and len(_keys) < key_count:
            print("%s keys were requested to be used, but a maximum of %s could be "
                  "found/made on the developer site, as it has a maximum of 10 keys per account. "
                  "Please delete some keys or lower your `key_count` level."
                  "I will use %s keys for the life of this client.", )

        if len(_keys) == 0:
            raise RuntimeError(
                "There are {} API keys already created and none match a key_name of '{}'."
                "Please specify a key_name kwarg, or go to 'https://developer.clashofclans.com' to delete "
                "unused keys.".format(len(keys), key_names)
            )

        await session.close()
        #print("Successfully initialised keys for use.")
        for k in _keys:
            total_keys.append(k)

    print(len(total_keys))
    return (total_keys)

def create_keys():
    done = False
    while done is False:
        try:
            loop = asyncio.get_event_loop()
            keys = loop.run_until_complete(get_keys(emails=emails,
                                     passwords=passwords, key_names="test", key_count=10))
            done = True
            return keys
        except Exception as e:
            done = False
            print(e)

class League(Struct):
    name : str

class ClanCapital(Struct):
    capitalHallLevel: Optional[int] = 0

class Location(Struct):
    name: str
    id: int

class Members(Struct):
    tag: str
    name: str
    expLevel: int
    trophies: int
    role: str
    builderBaseTrophies: int
    donations: int
    donationsReceived: int

class Clan(Struct):
    name: str
    tag: str
    type: str
    clanLevel: int
    members: int
    clanPoints: int
    clanCapitalPoints: int
    capitalLeague: League
    warLeague: League
    warWinStreak: int
    warWins: int
    clanCapital: ClanCapital
    memberList : List[Members]
    location: Optional[Location] = None



async def broadcast(keys):

    while True:
        async def fetch(url, session: aiohttp.ClientSession, headers):
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return (await response.read())
                return None


        pipeline = [{"$match" : {}}, { "$group" : { "_id" : "$tag" } } ]
        all_tags = [x["_id"] for x in (await clan_tags.aggregate(pipeline).to_list(length=None))]
        size_break = 50000
        all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]


        member_store = {}

        for tag_group in all_tags:
            tasks = []
            deque = collections.deque
            connector = aiohttp.TCPConnector(limit=250, ttl_dns_cache=300)
            keys = deque(keys)
            timeout = aiohttp.ClientTimeout(total=1800)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                for tag in tag_group:
                    tag = tag.replace("#", "%23")
                    keys.rotate(1)
                    tasks.append(fetch(f"https://api.clashofclans.com/v1/clans/{tag}", session, {"Authorization": f"Bearer {keys[0]}"}))
                responses = await asyncio.gather(*tasks)
                await session.close()

            changes = []
            raid_week = gen_raid_date()
            season = gen_season_date()
            for response in responses: #type: bytes
                # we shouldnt have completely invalid tags, they all existed at some point
                if response is None:
                    continue
                try:
                    clan = decode(response, type=Clan)
                    if clan.members == 0:
                        changes.append(DeleteOne({"tag": clan.tag}))
                    else:
                        members = [{"name": member.name, "tag" : member.tag, "role" : member.role, "expLevel" : member.expLevel, "trophies" : member.trophies,
                                    "builderTrophies" : member.builderBaseTrophies, "donations" : member.donations, "donationsReceived" : member.donationsReceived}
                                   for member in clan.memberList]
                        for member in clan.memberList:
                            member_store[member.tag] = (member)
                        changes.append(UpdateOne({"tag": clan.tag},
                                                      {"$set":
                                                           {"name": clan.name,
                                                            "members" : clan.members,
                                                            "level" : clan.clanLevel,
                                                            "type" : clan.type,
                                                            "location" : {"id" :clan.location.id if clan.location else clan.location, "name" : clan.location.name if clan.location else clan.location},
                                                            "clanCapitalPoints" : clan.clanCapitalPoints,
                                                            "clanPoints" : clan.clanPoints,
                                                            "capitalLeague" : clan.capitalLeague.name,
                                                            "warLeague" : clan.warLeague.name,
                                                            "warWinStreak" : clan.warWinStreak,
                                                            "warWins" : clan.warWins,
                                                            "clanCapitalHallLevel" : clan.clanCapital.capitalHallLevel,
                                                            "isValid" : clan.members >= 5,
                                                            f"changes.clanCapital.{raid_week}": {"trophies" : clan.clanCapitalPoints, "league" : clan.capitalLeague.name},
                                                            f"changes.clanWarLeague.{season}": {
                                                                "league": clan.warLeague.name},
                                                            "memberList": members
                                                            },
                                                       },
                                                      upsert=True))
                except Exception:
                    continue
            if changes:
                results = await clan_tags.bulk_write(changes, ordered=False)
                print(results.bulk_api_result)

        ranking_dict = {}
        member_sort = [v for v in member_store.values()]
        member_sort.sort(key=lambda x : x.trophies, reverse=True) #trophy sort
        for count, member in enumerate(member_sort[:250000], 1):
            ranking_dict[member.tag] = {"name": member.name, "trophies" : member.trophies, "trophiesRank" : count}

        member_sort.sort(key=lambda x: x.builderBaseTrophies, reverse=True)  # builder trophy sort
        for count, member in enumerate(member_sort[:250000], 1):
            prev_dict = ranking_dict.get(member.tag, {})
            ranking_dict[member.tag] = prev_dict | {"name": member.name, "builderTrophies": member.builderBaseTrophies, "builderTrophiesRank": count}

        member_sort.sort(key=lambda x: x.donations, reverse=True)  # donation sort
        for count, member in enumerate(member_sort[:250000], 1):
            prev_dict = ranking_dict.get(member.tag, {})
            ranking_dict[member.tag] = prev_dict | {"name": member.name, "donations": member.donations, "donationsRank": count}

        member_sort.sort(key=lambda x: x.donationsReceived, reverse=True)  # donation sort
        for count, member in enumerate(member_sort[:250000], 1):
            prev_dict = ranking_dict.get(member.tag, {})
            ranking_dict[member.tag] = prev_dict | {"name": member.name, "donationsReceived": member.donationsReceived, "donationsReceivedRank": count}


        await rankings.bulk_write([UpdateOne({"_id" : tag}, d, upsert=True) for tag, d in ranking_dict.items()], ordered=False)
        print(f"{len(ranking_dict)} Members Updated")
        await rankings.delete_many({"_id" : {"$nin" : list(ranking_dict.keys())}})


def gen_raid_date():
    now = datetime.utcnow().replace(tzinfo=utc)
    current_dayofweek = now.weekday()
    if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
            current_dayofweek == 0 and now.hour < 7):
        if current_dayofweek == 0:
            current_dayofweek = 7
        fallback = current_dayofweek - 4
        raidDate = (now - timedelta(fallback)).date()
        return str(raidDate)
    else:
        forward = 4 - current_dayofweek
        raidDate = (now + timedelta(forward)).date()
        return str(raidDate)

def gen_season_date():
    end = coc.utils.get_season_end().replace(tzinfo=utc).date()
    month = end.month
    if end.month <= 9:
        month = f"0{month}"
    return f"{end.year}-{month}"

loop = asyncio.get_event_loop()
keys = create_keys()
loop.create_task(broadcast(keys))
loop.run_forever()
