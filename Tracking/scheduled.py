import os
import time
from typing import Optional
from base64 import b64decode as base64_b64decode
from json import loads as json_loads
from datetime import datetime
from dotenv import load_dotenv
from msgspec.json import decode
from msgspec import Struct
from pymongo import UpdateOne, DeleteOne, InsertOne
from datetime import timedelta
from asyncio_throttle import Throttler
from pytz import utc
from statistics import mean
from collections import defaultdict

import motor.motor_asyncio
import collections
import aiohttp
import asyncio
import ujson
import coc
import numpy as np
import random
import string

locations = ["global", 32000007, 32000008, 32000009, 32000010, 32000011, 32000012, 32000013, 32000014, 32000015, 32000016,
             32000017,
             32000018, 32000019, 32000020, 32000021, 32000022, 32000023, 32000024, 32000025, 32000026, 32000027,
             32000028,
             32000029, 32000030, 32000031, 32000032, 32000033, 32000034, 32000035, 32000036, 32000037, 32000038,
             32000039,
             32000040, 32000041, 32000042, 32000043, 32000044, 32000045, 32000046, 32000047, 32000048, 32000049,
             32000050,
             32000051, 32000052, 32000053, 32000054, 32000055, 32000056, 32000057, 32000058, 32000059, 32000060,
             32000061,
             32000062, 32000063, 32000064, 32000065, 32000066, 32000067, 32000068, 32000069, 32000070, 32000071,
             32000072,
             32000073, 32000074, 32000075, 32000076, 32000077, 32000078, 32000079, 32000080, 32000081, 32000082,
             32000083,
             32000084, 32000085, 32000086, 32000087, 32000088, 32000089, 32000090, 32000091, 32000092, 32000093,
             32000094,
             32000095, 32000096, 32000097, 32000098, 32000099, 32000100, 32000101, 32000102, 32000103, 32000104,
             32000105,
             32000106, 32000107, 32000108, 32000109, 32000110, 32000111, 32000112, 32000113, 32000114, 32000115,
             32000116,
             32000117, 32000118, 32000119, 32000120, 32000121, 32000122, 32000123, 32000124, 32000125, 32000126,
             32000127,
             32000128, 32000129, 32000130, 32000131, 32000132, 32000133, 32000134, 32000135, 32000136, 32000137,
             32000138,
             32000139, 32000140, 32000141, 32000142, 32000143, 32000144, 32000145, 32000146, 32000147, 32000148,
             32000149,
             32000150, 32000151, 32000152, 32000153, 32000154, 32000155, 32000156, 32000157, 32000158, 32000159,
             32000160,
             32000161, 32000162, 32000163, 32000164, 32000165, 32000166, 32000167, 32000168, 32000169, 32000170,
             32000171,
             32000172, 32000173, 32000174, 32000175, 32000176, 32000177, 32000178, 32000179, 32000180, 32000181,
             32000182,
             32000183, 32000184, 32000185, 32000186, 32000187, 32000188, 32000189, 32000190, 32000191, 32000192,
             32000193,
             32000194, 32000195, 32000196, 32000197, 32000198, 32000199, 32000200, 32000201, 32000202, 32000203,
             32000204,
             32000205, 32000206, 32000207, 32000208, 32000209, 32000210, 32000211, 32000212, 32000213, 32000214,
             32000215,
             32000216, 32000217, 32000218, 32000219, 32000220, 32000221, 32000222, 32000223, 32000224, 32000225,
             32000226,
             32000227, 32000228, 32000229, 32000230, 32000231, 32000232, 32000233, 32000234, 32000235, 32000236,
             32000237,
             32000238, 32000239, 32000240, 32000241, 32000242, 32000243, 32000244, 32000245, 32000246, 32000247,
             32000248,
             32000249, 32000250, 32000251, 32000252, 32000253, 32000254, 32000255, 32000256, 32000257, 32000258,
             32000259, 32000260, 32000006]

keys = []
load_dotenv()

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("DB_LOGIN"))
looper = client.get_database("looper")
clan_tags = looper.get_collection("clan_tags")
collection_class = clan_tags.__class__

player_history: collection_class = client.new_looper.player_history
new_history: collection_class = client.new_looper.new_player_history
cwl_group: collection_class = client.new_looper.cwl_group
clan_war: collection_class = client.looper.clan_war
attack_db: collection_class = client.looper.warhits

ranking_history: collection_class = client.ranking_history
player_trophies: collection_class = ranking_history.player_trophies
player_versus_trophies: collection_class = ranking_history.player_versus_trophies
clan_trophies: collection_class = ranking_history.clan_trophies
clan_versus_trophies: collection_class = ranking_history.clan_versus_trophies
capital: collection_class = ranking_history.capital

rankings = client.get_database("rankings")
donation_rankings: collection_class = rankings.donations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
throttler = Throttler(rate_limit=200, period=1)
scheduler = AsyncIOScheduler(timezone=utc)
scheduler.start()

emails = []
passwords = []
#14-17 (18)
for x in range(14,18):
    emails.append(f"apiclashofclans+test{x}@gmail.com")
    passwords.append(os.getenv("COC_PASSWORD"))

coc_client = coc.Client(key_count=10, throttle_limit=25, cache_max_size=0, raw_attribute=True)

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


@scheduler.scheduled_job("cron", day_of_week="mon", hour=10)
async def store_clan_capital():
    async def fetch(url, session: aiohttp.ClientSession, headers, tag):
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return ((await response.json()), tag)
            return (None, None)


    global keys
    pipeline = [{"$match": {}}, {"$group": {"_id": "$tag"}}]
    all_tags = [x["_id"] for x in (await clan_tags.aggregate(pipeline).to_list(length=None))]
    size_break = 50000
    all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]

    for tag_group in all_tags:
        tasks = []
        deque = collections.deque
        connector = aiohttp.TCPConnector(limit=250, ttl_dns_cache=300)
        keys = deque(keys)
        timeout = aiohttp.ClientTimeout(total=1800)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, json_serialize=ujson.dumps) as session:
            for tag in tag_group:
                keys.rotate(1)
                tasks.append(fetch(f"https://api.clashofclans.com/v1/clans/{tag.replace('#', '%23')}/capitalraidseasons?limit=1", session,
                                   {"Authorization": f"Bearer {keys[0]}"}, tag))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()

        changes = []
        responses = [r for r in responses if type(r) is tuple]
        for response, tag in responses:
            try:
                # we shouldnt have completely invalid tags, they all existed at some point
                if response is None:
                    continue
                if len(response["items"]) == 0:
                    continue
                date = coc.Timestamp(data=response["items"][0]["endTime"])
                #-3600 = 1 hour has passed
                if 60 >= date.seconds_until >= -86400:
                    changes.append(InsertOne({"clan_tag" : tag, "data" : response["items"][0]}))
            except:
                pass

        await looper.raid_weekends.bulk_write(changes)


@scheduler.scheduled_job("cron", day="9-12", hour="*", minute=35)
async def store_cwl():
    season = gen_season_date()
    async def fetch(url, session: aiohttp.ClientSession, headers, tag):
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return ((await response.json()), tag)
            return (None, None)


    global keys
    pipeline = [{"$match": {}}, {"$group": {"_id": "$tag"}}]
    all_tags = [x["_id"] for x in (await clan_tags.aggregate(pipeline).to_list(length=None))]

    pipeline = [{"$match": {"$and" : [{"data.season" : season}, {"data.state" : "ended"}]}}, {"$group": {"_id": "$data.clans.tag"}}]
    done_for_this_season = [x["_id"] for x in (await cwl_group.aggregate(pipeline).to_list(length=None))]
    done_for_this_season = set([j for sub in done_for_this_season for j in sub])

    all_tags = [tag for tag in all_tags if tag not in done_for_this_season]

    size_break = 50000
    all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]

    was_found_in_a_previous_group = set()
    for tag_group in all_tags:
        tasks = []
        deque = collections.deque
        connector = aiohttp.TCPConnector(limit=250, ttl_dns_cache=300)
        keys = deque(keys)
        timeout = aiohttp.ClientTimeout(total=1800)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, json_serialize=ujson.dumps) as session:
            for tag in tag_group:
                if tag in was_found_in_a_previous_group:
                    continue
                keys.rotate(1)
                tasks.append(fetch(f"https://api.clashofclans.com/v1/clans/{tag.replace('#', '%23')}/currentwar/leaguegroup", session,
                                   {"Authorization": f"Bearer {keys[0]}"}, tag))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()

        changes = []
        responses = [r for r in responses if type(r) is tuple]
        for response, tag in responses:
            try:
                # we shouldnt have completely invalid tags, they all existed at some point
                if response is None:
                    continue
                season = response.get("season")
                for clan in response.get("clans"):
                    was_found_in_a_previous_group.add(clan.get("tag"))
                tags = sorted([clan.get("tag").replace('#','') for clan in response.get("clans")])
                cwl_id = f"{season}-{'-'.join(tags)}"
                changes.append(UpdateOne({"cwl_id" : cwl_id}, {"$set" : {"data" : response}}, upsert=True))
            except:
                pass
        if changes:
            await cwl_group.bulk_write(changes)
            print(f"{len(changes)} Changes Updated/Inserted")


#@scheduler.scheduled_job("cron", day="12", hour="1-22", minute=10)
@scheduler.scheduled_job("cron", day="19", hour="0", minute=54)
async def store_rounds():
    season = gen_season_date()
    pipeline = [{"$match": {"data.season": season}},
                {"$group": {"_id": "$data.rounds.warTags"}}]
    result = await cwl_group.aggregate(pipeline).to_list(length=None)
    done_for_this_season = [x["_id"] for x in result]
    done_for_this_season = [j for sub in done_for_this_season for j in sub]
    all_tags = list(set([j for sub in done_for_this_season for j in sub]))
    print(f"{len(all_tags)} war tags")
    size_break = 50000
    all_tags = [all_tags[i:i + size_break] for i in range(0, len(all_tags), size_break)]
    global keys
    global coc_client
    async def fetch(url, session: aiohttp.ClientSession, headers, tag):
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return ((await response.json()), tag)
            return (None, None)


    for tag_group in all_tags:
        tasks = []
        deque = collections.deque
        connector = aiohttp.TCPConnector(limit=250, ttl_dns_cache=300)
        keys = deque(keys)
        timeout = aiohttp.ClientTimeout(total=1800)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, json_serialize=ujson.dumps) as session:
            for tag in tag_group:
                keys.rotate(1)
                tasks.append(fetch(f"https://api.clashofclans.com/v1/clanwarleagues/wars/{tag.replace('#', '%23')}", session,
                                   {"Authorization": f"Bearer {keys[0]}"}, tag))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            await session.close()

        add_war = []
        add_war_hits = []
        responses = [r for r in responses if type(r) is tuple]
        for response, tag in responses:
            try:
                # we shouldnt have completely invalid tags, they all existed at some point
                if response is None:
                    continue
                response["tag"] = tag
                response["season"] = season
                war = coc.ClanWar(data=response, client=coc_client)
                war_alr = await clan_war.find_one({"war_id" : f"{war.clan.tag}-{int(war.preparation_start_time.time.timestamp())}"})
                if war_alr is None:
                    source = string.ascii_letters
                    custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()
                    is_used = await clan_war.find_one({"custom_id": custom_id})
                    while is_used is not None:
                        custom_id = str(''.join((random.choice(source) for i in range(6)))).upper()
                        is_used = await clan_war.find_one({"custom_id": custom_id})
                    add_war.append(UpdateOne(
                        {"war_id": f"{war.clan.tag}-{int(war.preparation_start_time.time.timestamp())}"},
                        {"$set": {
                            "custom_id": custom_id,
                            "data": war._raw_data}}, upsert=True
                        ))
                else:
                    custom_id = war_alr.get("custom_id")
                for attack in war.attacks:
                    add_war_hits.append(UpdateOne(
                        {"$and" : [{"tag" : attack.attacker_tag},
                        {"defender_tag" : attack.defender_tag},
                        {"war_start" : int(war.preparation_start_time.time.timestamp())}]},
                        {
                        "tag": attack.attacker.tag,
                        "name": attack.attacker.name,
                        "townhall": attack.attacker.town_hall,
                        "_time": int(war.preparation_start_time.time.timestamp()),
                        "destruction": attack.destruction,
                        "stars": attack.stars,
                        "fresh": attack.is_fresh_attack,
                        "war_start": int(war.preparation_start_time.time.timestamp()),
                        "defender_tag": attack.defender.tag,
                        "defender_name": attack.defender.name,
                        "defender_townhall": attack.defender.town_hall,
                        "war_type": str(war.type),
                        "war_status": str(war.status),
                        "attack_order": attack.order,
                        "map_position": attack.attacker.map_position,
                        "war_size": war.team_size,
                        "clan": attack.attacker.clan.tag,
                        "clan_name": attack.attacker.clan.name,
                        "defending_clan": attack.defender.clan.tag,
                        "defending_clan_name": attack.defender.clan.name,
                        "season" : season,
                        "full_war": custom_id
                        }, upsert=True))
            except:
                pass
        if add_war:
            try:
                await clan_war.bulk_write(add_war, ordered=False)
                print(f"{len(add_war)} Wars Updated/Inserted")
            except:
                print(f"{len(add_war)} Wars Updated/Inserted")
        if add_war_hits:
            try:
                await attack_db.bulk_write(add_war_hits, ordered=False)
                print(f"{len(add_war_hits)} Attacks Updated/Inserted")
            except:
                print(f"{len(add_war_hits)} Attacks Updated/Inserted")




@scheduler.scheduled_job("cron", hour=4, minute=56)
async def store_all_leaderboards():
    for database, function in \
            zip([clan_trophies, clan_versus_trophies, capital, player_trophies, player_versus_trophies],
                [coc_client.get_location_clans, coc_client.get_location_clans_versus, coc_client.get_location_clans_capital, coc_client.get_location_players, coc_client.get_location_players_versus]):


        tasks = []
        for location in locations:
            task = asyncio.ensure_future(function(location_id=location))
            tasks.append(task)
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        store_tasks = []
        for index, response in enumerate(responses):
            if isinstance(response, coc.NotFound):
                continue
            location = locations[index]
            store_tasks.append(InsertOne({"location" : location,
                                          "date" : str(datetime.now(tz=utc).date()),
                                          "data" : {"items": [x._raw_data for x in response]}}))

        await database.bulk_write(store_tasks)

def gen_season_date():
    end = coc.utils.get_season_end().replace(tzinfo=utc).date()
    month = end.month
    if end.month <= 9:
        month = f"0{month}"
    return f"{end.year}-{month}"

loop = asyncio.get_event_loop()
keys = create_keys()
coc_client.login_with_keys(*keys[:10])
loop.run_forever()
