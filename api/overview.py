from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from api.dependencies.mongo import get_database
from api.utils import serialize_doc

overview_router = APIRouter()


@overview_router.get("/overview/{groupId}/summary", tags=["overview"])
async def get_overview_summary(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    players = await db["players"].find({"groupId": groupId}).to_list()
    matches = await db["matches"].find({"groupId": groupId}).to_list()
    tournaments = await db["tournaments"].find({"groupId": groupId}).to_list()
    return {
        "total_players": len(players),
        "total_matches": len(matches),
        "total_tournaments": len(tournaments),
    }


@overview_router.get("/overview/{groupId}/players_by_win_rate", tags=["overview"])
async def get_players_by_win_rate(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    players = await db["players"].find({"groupId": groupId}).to_list()
    matches = await db["matches"].find({"groupId": groupId}).to_list()
    serialized_matches = [serialize_doc(m) for m in matches]

    result = []
    for p in players:
        p_doc = serialize_doc(p)
        name = p_doc.get("name")
        wins = 0
        losses = 0
        for m in serialized_matches:
            if m.get("player1") == name or m.get("player2") == name:
                if m.get("winner") == name:
                    wins += 1
                else:
                    losses += 1
        total = wins + losses
        win_rate = round(wins / total * 100, 1) if total > 0 else 0
        result.append({"name": name, "wins": wins, "losses": losses, "win_rate": win_rate})

    result.sort(key=lambda x: x["win_rate"], reverse=True)
    return {"players": result}


@overview_router.get("/overview/{groupId}/players_by_tournament_wins", tags=["overview"])
async def get_players_by_tournament_wins(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    players = await db["players"].find({"groupId": groupId}).to_list()
    tournaments = await db["tournaments"].find({"groupId": groupId}).to_list()

    tourn_wins: dict[str, int] = {}
    for t in tournaments:
        t_doc = serialize_doc(t)
        winner = t_doc.get("winner")
        if winner:
            tourn_wins[winner] = tourn_wins.get(winner, 0) + 1

    result = []
    for p in players:
        name = serialize_doc(p).get("name")
        result.append({"name": name, "tournament_wins": tourn_wins.get(name, 0)})

    result.sort(key=lambda x: x["tournament_wins"], reverse=True)
    return {"players": result}


@overview_router.get("/overview/{groupId}/players_by_match_wins", tags=["overview"])
async def get_players_by_match_wins(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    players = await db["players"].find({"groupId": groupId}).to_list()
    matches = await db["matches"].find({"groupId": groupId}).to_list()
    serialized_matches = [serialize_doc(m) for m in matches]

    result = []
    for p in players:
        name = serialize_doc(p).get("name")
        wins = sum(1 for m in serialized_matches if m.get("winner") == name)
        result.append({"name": name, "wins": wins})

    result.sort(key=lambda x: x["wins"], reverse=True)
    return {"players": result}


@overview_router.get("/overview/{groupId}/tournaments", tags=["overview"])
async def get_overview_tournaments(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    tournaments = await db["tournaments"].find({"groupId": groupId}).to_list()

    result = []
    for t in tournaments:
        t_doc = serialize_doc(t)
        date_str = t_doc.get("date", "")
        try:
            parsed_date = datetime.strptime(date_str, "%m-%d-%Y")
        except (ValueError, TypeError):
            parsed_date = datetime.min
        result.append({
            "name": t_doc.get("name"),
            "winner": t_doc.get("winner"),
            "date": date_str,
            "url": t_doc.get("url"),
            "_sort_date": parsed_date,
        })

    result.sort(key=lambda x: x["_sort_date"], reverse=True)
    for item in result:
        del item["_sort_date"]
    return {"tournaments": result}


@overview_router.get("/overview/{groupId}/tournaments_per_year", tags=["overview"])
async def get_tournaments_per_year(groupId: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    tournaments = await db["tournaments"].find({"groupId": groupId}).to_list()

    year_counts: dict[str, int] = {}
    for t in tournaments:
        t_doc = serialize_doc(t)
        date_str = t_doc.get("date", "")
        try:
            year = str(datetime.strptime(date_str, "%m-%d-%Y").year)
            year_counts[year] = year_counts.get(year, 0) + 1
        except (ValueError, TypeError):
            pass

    result = [{"year": year, "count": count} for year, count in year_counts.items()]
    result.sort(key=lambda x: x["year"])
    return {"tournaments_per_year": result}
