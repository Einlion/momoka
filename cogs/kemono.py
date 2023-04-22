# Polls kemono.party for new artworks.
import discord
from discord.ext import tasks, commands
import sqlite3
from datetime import datetime as time
from datetime import timezone as tz
import aiohttp
import utils.fetch as ufetch
import asyncio

KEMONO_BASE_HOST = "https://kemono.party"
KEMONO_CREATOR_URL = KEMONO_BASE_HOST + "/api/creators"
KEMONO_DB_PATH = "data/kemono.db"
KEMONO_TABLE_NAME = "kemono"
KEMONO_SCHEMA = f"""
    CREATE TABLE IF NOT EXISTS {KEMONO_TABLE_NAME} (
        service TEXT NOT NULL,
        uid TEXT NOT NULL,
        UNIQUE(service, uid)
);"""


class Kemono(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timestamp = time.now(tz.utc).replace(tzinfo=None)

        with sqlite3.connect(
            KEMONO_DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        ) as c:
            c.execute(KEMONO_SCHEMA)

    async def cog_unload(self):
        self.cancel_schedulers()
        await super().cog_unload()

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    def cancel_schedulers(self):
        try:
            self.updates_scheduler.cancel()
            self.follows_scheduler.cancel()
        except:
            pass

    def start_schedulers(self):
        self.cancel_schedulers()
        self.find_updated_artists.start()

    @commands.command()
    async def start(self, ctx):
        self.destination = ctx.channel
        self.start_schedulers()
        await ctx.send("Channel successfully set for new updates")

    @commands.command()
    async def stop(self, ctx):
        self.cancel_schedulers()
        await ctx.send("Successfully stopped")

    @commands.group(invoke_without_command=True)
    async def kemono(self, ctx):
        print(ctx.invoked_subcommand)
        """Manage Kemono artists"""
        if ctx.invoked_subcommand is None:
            raise commands.errors.BadArgument

    @kemono.command()
    async def add(self, ctx, link: str):
        try:
            tokens = link.split("kemono.party/")[1].split("/")
            (service, uid) = (tokens[0], tokens[2])
        except:
            raise commands.ArgumentParsingError("Kemono link")

        with sqlite3.connect(KEMONO_DB_PATH) as c:
            c.execute(
                f'INSERT OR IGNORE INTO {KEMONO_TABLE_NAME} VALUES ("{service}", "{uid}")'
            )
            c.commit()

        await ctx.send("Added successfully")

    @kemono.command()
    async def remove(self, ctx, link: str):
        try:
            tokens = link.split("kemono.party/")[1].split("/")
            (service, uid) = (tokens[0], tokens[2])
        except:
            raise commands.ArgumentParsingError("Kemono link")

        with sqlite3.connect(KEMONO_DB_PATH) as c:
            c.execute(
                f'DELETE FROM {KEMONO_TABLE_NAME} WHERE service="{service}" AND uid="{uid}"'
            )
            c.commit()

        await ctx.send("Removed successfully")

    @tasks.loop(seconds=10)
    async def find_updated_artists(self):
        session = aiohttp.ClientSession()
        async with session as s:
            artists = await ufetch.fetchJSON(s, KEMONO_CREATOR_URL)
        with sqlite3.connect(KEMONO_DB_PATH) as c:
            watching = c.execute(f"SELECT * from {KEMONO_TABLE_NAME}").fetchall()

        bucket = []
        for artist in artists:
            if (artist["service"], artist["id"]) in watching:
                # There's an offset parameter by ?o={offset} but we don't need it for this usecase
                bucket.append(
                    (
                        artist["name"],
                        artist["service"],
                        artist["id"],
                        f"{KEMONO_BASE_HOST}/api/{artist['service']}/user/{artist['id']}",
                    )
                )
        current_time = time.now(tz.utc)
        r = await asyncio.gather(*[self.find_new_posts(*_) for _ in bucket])
        for el in r:
            for post in el:
                await self.destination.send(embed=self.generate_embed(*post))
                await asyncio.sleep(1)
        self.timestamp = current_time.replace(tzinfo=None)

    async def find_new_posts(self, name, service, id, url):
        async with aiohttp.ClientSession() as s:
            # First 50 posts are available at initial offset (should be plenty)
            posts = await ufetch.fetchJSON(s, url)
            new_posts = filter(
                (
                    lambda post: time.strptime(
                        post["added"], "%a, %d %b %Y %H:%M:%S %Z"
                    )
                    > self.timestamp
                ),
                posts,
            )

            bucket = []
            for post in new_posts:
                if len(post["attachments"]) > 0:
                    image_url = KEMONO_BASE_HOST + post["attachments"][0]["path"]
                    title = post["content"]
                    post_url = (
                        KEMONO_BASE_HOST
                        + "/"
                        + service
                        + "/user/"
                        + id
                        + "/post/"
                        + post["id"]
                    )
                    bucket.append((image_url, name, id, service, title, post_url))
            return bucket

    @staticmethod
    def generate_embed(
        image_url, artist_name, artist_id, service, post_title, post_url
    ):
        embed = (
            discord.Embed(color=0x8c97e6, description=post_title)
            .set_image(url=image_url)
            .set_footer(text="\n")
            .set_author(
                name=artist_name,
                icon_url=KEMONO_BASE_HOST + "/icons/" + service + "/" + artist_id,
            )
        )
        embed.title = service.capitalize()
        embed.description += f"\n\n[Link]({post_url})"
        return embed


async def setup(bot):
    kemono_cog = Kemono(bot)
    await bot.add_cog(kemono_cog)
