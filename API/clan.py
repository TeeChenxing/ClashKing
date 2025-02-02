
import coc

from collections import defaultdict
from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from APIUtils.utils import fix_tag, leagues, db_client
from bson.objectid import ObjectId

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Clan Endpoints"])


#CLAN ENDPOINTS
@router.get("/clan/{clan_tag}/stats",
         name="All stats for a clan (activity, donations, etc)")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_historical(clan_tag: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    result = await db_client.clan_stats.find_one({"tag": clan_tag})
    if result is not None:
        del result["_id"]
    return result



@router.get("/clan/{clan_tag}/basic",
         name="Basic Clan Object")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_basic(clan_tag: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    result = await db_client.basic_clan.find_one({"tag": clan_tag})
    if result is not None:
        del result["_id"]
    return result



@router.get("/clan/{clan_tag}/join-leave/{season}",
         name="Join Leaves in a season")
@cache(expire=300)
@limiter.limit("5/second")
async def clan_join_leave(clan_tag: str, season: str, request: Request, response: Response):
    clan_tag = fix_tag(clan_tag)
    year = season[:4]
    month = season[-2:]
    season_start = coc.utils.get_season_start(month=int(month) - 1, year=int(year))
    season_end = coc.utils.get_season_end(month=int(month) - 1, year=int(year))
    result = await db_client.clan_join_leave.find({"$and": [{"tag": clan_tag},
                                                          {"time": {"$gte": season_start.timestamp()}},
                                                          {"time": {"$lte": season_end.timestamp()}}]}).sort("time", 1).to_list(length=None)
    if result:
        for r in result:
            del r["_id"]
    return dict(result)





@router.get("/clan/search",
         name="Search Clans by Filtering")
@cache(expire=300)
@limiter.limit("1/second")
async def clan_filter(request: Request, response: Response,  limit: int= 100, location_id: int = None, minMembers: int = None, maxMembers: int = None,
                      minLevel: int = None, maxLevel: int = None, openType: str = None,
                          minWarWinStreak: int = None, minWarWins: int = None, minClanTrophies: int = None, maxClanTrophies: int = None, capitalLeague: str= None,
                          warLeague: str= None, memberList: bool = True, before:str =None, after: str=None):
    queries = {}
    queries['$and'] = []
    if location_id:
        queries['$and'].append({'location.id': location_id})

    if minMembers:
        queries['$and'].append({"members": {"$gte" : minMembers}})

    if maxMembers:
        queries['$and'].append({"members": {"$lte" : maxMembers}})

    if minLevel:
        queries['$and'].append({"level": {"$gte" : minLevel}})

    if maxLevel:
        queries['$and'].append({"level": {"$lte" : maxLevel}})

    if openType:
        queries['$and'].append({"type": openType})

    if capitalLeague:
        queries['$and'].append({"capitalLeague": capitalLeague})

    if warLeague:
        queries['$and'].append({"warLeague": warLeague})

    if minWarWinStreak:
        queries['$and'].append({"warWinStreak": {"$gte": minWarWinStreak}})

    if minWarWins:
        queries['$and'].append({"warWins": {"$gte": minWarWins}})

    if minClanTrophies:
        queries['$and'].append({"clanPoints": {"$gte": minClanTrophies}})

    if maxClanTrophies:
        queries['$and'].append({"clanPoints": {"$gte": maxClanTrophies}})

    if after:
        queries['$and'].append({"_id": {"$gt": ObjectId(after)}})

    if before:
        queries['$and'].append({"_id": {"$lt": ObjectId(before)}})


    if queries["$and"] == []:
        queries = {}

    limit = min(limit, 1000)
    results = await db_client.basic_clan.find(queries).limit(limit).sort("_id", 1).to_list(length=limit)
    return_data = {"items" : [], "before": "", "after" : ""}
    if results:
        return_data["before"] = str(results[0].get("_id"))
        return_data["after"] = str(results[-1].get("_id"))
        for data in results:
            del data["_id"]
            if not memberList:
                del data["memberList"]
        return_data["items"] = results
    return return_data
