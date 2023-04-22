import json


async def fetchJSON(session, url):
    async with session.get(url) as response:
        return await response.json()
