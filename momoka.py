import logging
import logging.handlers
import traceback
import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True


class Emilico(commands.AutoShardedBot):
    # Using default init for now

    async def setup_hook(self):
        extensions = [
            f"cogs.{extension[:-3]}"
            for extension in os.listdir("cogs")
            if extension.endswith(".py")
        ]
        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(extension)
            except Exception as e:
                print(
                    "Failed to load extension {}\n{}: {}".format(
                        extension, type(e).__name__, e
                    )
                )
                traceback.print_exc()

    async def on_command_error(self, ctx, error: commands.CommandError):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send("This command cannot be used in private messages.")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send("Sorry. This command is disabled and cannot be used.")
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                self.logger.exception(
                    "In %s:", ctx.command.qualified_name, exc_info=original
                )
            await ctx.send("Internal exception occured, check logs.")
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send("Unable to parse: " + str(error))


async def start_bot(token):
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    async with Emilico(
        command_prefix=commands.when_mentioned_or("."), intents=intents
    ) as bot:
        bot.logger = logger
        await bot.start(token)


try:
    asyncio.run(start_bot(os.getenv("BOT_TOKEN")))
except KeyboardInterrupt:
    pass
