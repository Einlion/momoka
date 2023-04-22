# Misc QoL commands
from discord.ext import tasks, commands


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["r"])
    async def reload(self, ctx):
        utils = []
        for i in self.bot.extensions:
            utils.append(i)
        l = len(utils)
        for i in utils:
            await self.bot.unload_extension(i)
            try:
                await self.bot.load_extension(i)
            except Exception as e:
                await ctx.send(
                    "Failed to reload module `{}` ``` {}: {} ```".format(
                        i, type(e).__name__, e
                    )
                )
                l -= 1
        await ctx.send("Reloaded {} of {} modules.".format(l, len(utils)))


async def setup(bot):
    misc = Misc(bot)
    await bot.add_cog(misc)
