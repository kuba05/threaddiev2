from typing import cast
import re, sys
import asyncio

import discord

from constants import ARCHIVING_CHANNELS_AT_ONCE, SEASON_GAME_MASK, OUTOFSEASON_GAME_MASK, TODO_ARCHIVE_CATEGORY_NAME, DONE_ARCHIVE_CATEGORY_NAME, THE_ARCHIVE_CATEGORY_NAME, QUITE_CATEGORY_NAME

async def getCategoryByName(ctx: discord.ApplicationContext, name: str):
    category = discord.utils.get(ctx.guild.categories, name = name)
    if category == None:
        category = await ctx.guild.create_category(name)
    return cast(discord.CategoryChannel, category)


async def moveChannelIntoAThread(ctx: discord.ApplicationContext, channel: discord.TextChannel, place: discord.TextChannel, name: str):
    if not channel.can_send():
        await ctx.channel.send("Could not convert channel.\nIs the channel private?")
        return

    # Create webhook to emulate users posting in channels
    hook = await place.create_webhook(name="Channel to Thread [DELETE IF FOUND]", reason="Moving channel to thread")

    try:
        # Create a new thread
        thread = await place.create_thread(name=name, type=discord.ChannelType.public_thread, reason=f"Moved channel: `{channel}` to a thread")

        # Create a list of messages from the selected channel
        history = await channel.history(limit=None, oldest_first=True).flatten()

        for msg in history:
            try:
                await hook.send(
                    msg.content,
                    username = msg.author.display_name if type(msg.author) == discord.Member else msg.author.name,
                    avatar_url = msg.author.display_avatar.url,
                    embeds = msg.embeds,
                    thread = thread,
                    files = [await f.to_file() for f in msg.attachments],
                    allowed_mentions = discord.AllowedMentions.none()
                )
                
            # Pinned message notifications will be caught as messages with no content
            except discord.errors.HTTPException as err:
                print(type(err), err)
            except Exception as e:
                print(e, file=sys.stderr, flush=True)
                await ctx.channel.send("Unknown error!")
                await ctx.channel.send(type(e), e)


        await thread.remove_user(cast(discord.ClientUser, ctx.bot.user))
        await ctx.channel.send(f"Moved channel `{channel}` to a thread in `{place}`")

    except (TypeError, discord.DiscordException) as err:

        print(type(err), err)
        await ctx.channel.send(f"Could not move channel to thread\n{type(err)} {err}")

    finally:
        await hook.delete(reason=f"Moved channel `{channel}` to a thread in `{place}`. No longer needed")


def doesBelongToSeason(ctx: discord.ApplicationContext, channel: discord.TextChannel):
    """
    season is marked with the season's number, non-season games have 0. None if not a game channel.
    """
    matched = re.match(SEASON_GAME_MASK, channel.name)

    # matched as season game
    if matched:
        return matched.groups()[0]

    else:
        matched = re.match(OUTOFSEASON_GAME_MASK, channel.name)
        if matched:
            return 0
        
    return None

async def moveAllChannelsToBeArchived(ctx: discord.ApplicationContext):
    targetCategory: discord.CategoryChannel = await getCategoryByName(ctx, TODO_ARCHIVE_CATEGORY_NAME)
    
    for channel in ctx.guild.channels:
        if "archive" in channel.name.lower() and channel.type.name != "category" and not (channel.category and "archive" in channel.category.name.lower()):
            await channel.move(category=targetCategory, end=True)


async def archiveAllChannelsToBeArchived(ctx:discord.ApplicationContext):
    sourceCategory: discord.CategoryChannel = await getCategoryByName(ctx, TODO_ARCHIVE_CATEGORY_NAME)

    archiveCategory: discord.CategoryChannel = await getCategoryByName(ctx, THE_ARCHIVE_CATEGORY_NAME)

    moveToCategory: discord.CategoryChannel = await getCategoryByName(ctx, DONE_ARCHIVE_CATEGORY_NAME)

    quiteCategory: discord.CategoryChannel = await getCategoryByName(ctx, QUITE_CATEGORY_NAME)

    channelsToArchive: list[tuple[discord.TextChannel, discord.TextChannel]] = []
    
    for channel in sourceCategory.text_channels:
        seasonNumber = doesBelongToSeason(ctx, channel)
        
        # we can't auto archive non-games channels
        if seasonNumber == None:
            continue

        if seasonNumber == 0:
            targetName = "other-games"
        else:
            targetName = f"season-{seasonNumber}"

        # https://stackoverflow.com/questions/2361426/get-the-first-item-from-an-iterable-that-matches-a-condition
        channelToArchiveInto = next((channel for channel in archiveCategory.text_channels if channel.name == targetName), None)

        if channelToArchiveInto == None:
            channelToArchiveInto = await archiveCategory.create_text_channel(targetName)
        channelToArchiveInto = cast(discord.TextChannel, channelToArchiveInto)

        channelsToArchive.append((channel, channelToArchiveInto))


    displacedChannels = list(set(x[1] for x in channelsToArchive))

    for channel in displacedChannels:
        await channel.edit(category=quiteCategory, sync_permissions=True)



    async def helperFunction(channels: tuple[discord.TextChannel,discord.TextChannel]):
        channelToArchive: discord.TextChannel = channels[0]
        channelToArchiveInto: discord.TextChannel = channels[1]
        await moveChannelIntoAThread(ctx=ctx, channel=channelToArchive, name=channelToArchive.name, place=channelToArchiveInto)
        await channelToArchive.move(category=moveToCategory, end=True)

    allPromises = [helperFunction(channels) for channels in channelsToArchive]

    # we will execute them in groups of 8s to make my life easier
    while len(allPromises) > 0:
        await asyncio.gather(*allPromises[:ARCHIVING_CHANNELS_AT_ONCE])
        allPromises = allPromises[ARCHIVING_CHANNELS_AT_ONCE:]
    
    for channel in displacedChannels:
        await channel.edit(category=archiveCategory, sync_permissions=True)


