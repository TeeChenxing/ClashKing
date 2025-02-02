from fastapi import  Request, Response, HTTPException
from fastapi import APIRouter
from fastapi_cache.decorator import cache
from typing import  Union
from slowapi import Limiter
from slowapi.util import get_remote_address
from APIUtils.utils import db_client, fix_tag


limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Leaderboard History"])

@router.get("/ranking/live/legends")
@cache(expire=300)
async def live_legend_rankings(request: Request, response: Response, top_ranking: int = 1, lower_ranking: int = 200):
    if abs((lower_ranking + 1) - top_ranking) >= 5000:
        raise HTTPException(status_code=400, detail="Max 5000 rankings can be pulled at one time")
    results = await db_client.legend_rankings.find({"rank" : {"$gte" : top_ranking, "$lte" : lower_ranking}}, {"_id" : 0}).to_list(length=None)
    return results

@router.get("/ranking/legends/{player_tag}")
@cache(expire=300)
async def live_legend_rankings(player_tag: str, request: Request, response: Response):
    player_tag = fix_tag(player_tag)
    result = await db_client.legend_rankings.find_one({"tag" : player_tag}, {"_id" : 0})
    return result

@router.get("/ranking/player-trophies/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def player_trophies_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await db_client.player_trophies.find_one({"$and" : [{"location" : location}, {"date" : date}]})
    return r.get("data")


@router.get("/ranking/player-builder/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def player_builder_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await db_client.player_versus_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")


@router.get("/ranking/clan-trophies/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_trophies_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await db_client.clan_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")


@router.get("/ranking/clan-builder/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_builder_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await db_client.clan_versus_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")


@router.get("/ranking/clan-capital/{location}/{date}",
         name="Top 200 Daily Leaderboard History. Date: yyyy-mm-dd")
@cache(expire=300)
@limiter.limit("30/second")
async def clan_capital_ranking(location: Union[int, str], date: str, request: Request, response: Response):
    r = await db_client.capital_trophies.find_one({"$and" : [{"date" : date}, {"location" : location}]})
    return r.get("data")