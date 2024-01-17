import json
import os
import asyncio

import discord
from dotenv import load_dotenv

from helper import onlyAuthorized, onlyGameMembersAndAuthorized
from archiving import moveChannelIntoAThread, moveAllChannelsToBeArchived, archiveAllChannelsToBeArchived
from constants import TODO_ARCHIVE_CATEGORY_NAME

load_dotenv()
TOKEN = os.getenv('TOKEN')
intents=discord.Intents.all()

bot = discord.Bot(intents=intents)




async def createChannel(ctx, name):
    channel = await ctx.guild.create_text_channel(name)
    await channel.set_permissions(bot.user, manage_threads=True, read_messages=True, send_messages=True)
    await channel.set_permissions(ctx.author, read_messages=True, manage_channels=True, send_messages=True)
    await channel.set_permissions(ctx.guild.default_role, read_messages=False)
    return channel


async def removeChannel(ctx, channel):
    await channel.delete()




"""@bot.slash_command(name="clear_webhooks", guild_ids=GUILD, description="remove all webhooks")
async def clear_webhooks(ctx):
    await ctx.defer(ephemeral=True)
    hooks = await ctx.guild.webhooks()
    print(hooks)
    print("detected:",len(hooks))
    async def xxx(h):
        await h.delete()
        print("done")
    for hook in hooks:
        print(hook.name)
        if hook.user != bot.user:
            print("not by the bot!")
    await asyncio.gather(*[xxx(hook) for hook in hooks if hook.user == bot.user])
    
    await ctx.followup.send(f"{x} webhooks deleted!")
"""


@onlyAuthorized
@bot.command(description="Behold!")
@discord.option("message", str, description = "speak, my child!")
async def speak(ctx, message: str):
    await ctx.defer(ephemeral=True)
    await ctx.channel.send(message)
    await ctx.followup.send("done")

"""
@bot.slash_command(name="dump_role", guild_ids=GUILD, description="Dump all players by assigned team")
async def dump_role(ctx, role: discord.Role):
    await ctx.defer(ephemeral=True)
    await ctx.followup.send(f"DUMPING ROLE {str(role)}")
    await ctx.followup.send("\n".join(str(member)for member in role.members))
"""

############
# ARCHIVES #
############
@onlyAuthorized
@bot.command(description = "Convert a channel to a thread with the option to remove the original channel")
@discord.option("channel", discord.TextChannel, description = "Select a channel to turn into a thread")
@discord.option("place", discord.TextChannel, description = "Select a channel to create the thread in")
@discord.option("name", str, description = "Enter a name for the thread [Default: Channel Name]", required=False, default="")
async def channel_to_thread(ctx, channel: discord.TextChannel, place: discord.TextChannel, name: str):
    await ctx.defer(ephemeral=True)

    if name == "": name = channel.name

    await ctx.followup.send(f"transfering channel: {channel.name}")
    await moveChannelIntoAThread(ctx, channel, place, name)
    await ctx.followup.send(f"done")
    
@onlyGameMembersAndAuthorized
@bot.command(description = "marks current channel as ready for archivation")
async def mark_archived(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral = True)

    if "archive" in ctx.channel.name:
        await ctx.followup.send("channel is already marked for archivation")
        return
    
    await ctx.channel.edit(name=ctx.channel.name+"-archive")
    await ctx.followup.send("channel now marked for archivation")
    
@onlyAuthorized
@bot.command(description = "move all channels marked for archivation into TODO archive")
async def move_marked_channels(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral = True)
    
    await moveAllChannelsToBeArchived(ctx)
    await ctx.followup.send("done")

@onlyAuthorized
@bot.command(description = "Archive all channels in TODO archive")
async def archive_waiting(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral = True)
    await archiveAllChannelsToBeArchived(ctx)
    await ctx.channel.send("done")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")



bot.run(TOKEN)