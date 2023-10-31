import json
import os
import asyncio

import discord
from discord import ButtonStyle
from discord.commands import Option
from discord.ui import InputText, Modal, View, Button, button
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
TOKEN = os.getenv('TOKEN')
GUILD = json.loads(os.getenv("GUILDS"))
ALLOWED = json.loads(os.getenv("ALLOWED"))
bot = discord.Bot(intents=discord.Intents.all())
#intents = discord.Intents().all()
#bot = discord.Bot(intents=intents)







async def createChannel(ctx, name):
    channel = await ctx.guild.create_text_channel(name)
    await channel.set_permissions(bot.user, manage_threads=True, read_messages=True, send_messages=True)
    await channel.set_permissions(ctx.author, read_messages=True, manage_channels=True, send_messages=True)
    await channel.set_permissions(ctx.guild.default_role, read_messages=False)
    return channel

async def hasPermissions(ctx):
    if (ctx.author.id not in ALLOWED):
        await ctx.followup.send("You are not allowed to use this command. If you believe that's a mistake, contact gavlna.")
        return False
    return True

async def moveChannelIntoAThread(ctx, channel, place, name):
    #FIXME: why can_send
    if not channel.can_send():
        await ctx.followup.send("Could not convert channel.\nIs the channel private?")
        return

    # Create webhook to emulate users posting in channels
    hook = await place.create_webhook(name="Channel to Thread [DELETE IF FOUND]", reason="Moving channel to thread")

    try:
        # Create a new thread
        thread = await place.create_thread(name=name or str(channel), type=discord.ChannelType.public_thread,
                                           reason=f"Moved channel: `{channel}` to a thread")

        # Create a list of messages from the selected channel
        hist = await channel.history(limit=None, oldest_first=True).flatten()
        for msg in hist:
            # Media that is marked as spoilers will need to be reuploaded due to bots not embedding spoilered URLs.
            # Any other media should be linked to just fine, working around the issue of Nitro uploads
            try:
                #await hook.send(msg.content + '\n'.join([f.url for f in msg.attachments if not f.is_spoiler()]),
                #                username=msg.author.display_name if type(msg.author) == discord.Member
                #                else msg.author.name, avatar_url=msg.author.display_avatar.url,
                #                embeds=msg.embeds, thread=thread,
                #                files=[await f.to_file() for f in msg.attachments if f.is_spoiler()])
                await hook.send(msg.content,
                                username=msg.author.display_name if type(msg.author) == discord.Member
                                else msg.author.name, avatar_url=msg.author.display_avatar.url,
                                embeds=msg.embeds, thread=thread,
                                files=[await f.to_file() for f in msg.attachments])
            # Pinned message notifications will be caught as messages with no content
            except discord.errors.HTTPException as err:
                print(type(err), err)
            except Exception as e:
                print("Unknown error!")
                print(type(e), e)


        await thread.remove_user(bot.user)
        await ctx.followup.send(f"Moved channel `{channel}` to a thread in `{place}`")
    except TypeError or discord.DiscordException as err:
        print(type(err), err)
        await ctx.followup.send(f"Could not move channel to thread\n{type(err)} {err}")
    finally:
        await hook.delete(reason=f"Moved channel `{channel}` to a thread in `{place}`. No longer needed")


async def removeChannel(ctx, channel):
    await channel.delete()










class ThreadModal(Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(InputText(label="Thread Name", placeholder="Super Thread"))

    async def callback(self, interaction: discord.Interaction):
        thread = await interaction.channel.create_thread(name=self.children[0].value,
                                                         type=discord.ChannelType.public_thread)
        await interaction.response.send_message(f"Created thread `{self.children[0].value}`", ephemeral=True)
        await thread.add_user(interaction.user)
        await thread.remove_user(bot.user)


@bot.slash_command(name="create_channel", guild_ids=GUILD, description="Create channel")
async def create_channel(ctx, channel_name: Option(str, "Select a channel name to create")):
    await ctx.defer(ephemeral=True)
    
    if not await hasPermissions(ctx): return
    
    await createChannel(ctx, channel_name)

    await ctx.followup.send("done")


@bot.slash_command(name="clear_webhooks", guild_ids=GUILD, description="remove all webhooks")
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


@bot.slash_command(name="check_a_season_is_archived", guild_ids=GUILD, description="Archive all games from a given season")
async def check_season_is_archived(ctx, name: Option(str, "enter season number please")):
    await ctx.defer(ephemeral=True)

    archive = None
    channelsToDo = []
    for channel in ctx.guild.text_channels:
        if channel.name == "archive-season-"+name:
            archive = channel
        if channel.name[1:2+len(name)] == "s"+name :
            print(f"selected {channel.name}")
            channelsToDo.append(channel)
   
    ogCount = len(channelsToDo)

    if archive == None:
        await ctx.followup.send("No archive found")
        return

    for thread in archive.threads:
        print(thread.name, flush=True)
        channelsToDo = list(filter(lambda channel: channel.name != thread.name, channelsToDo))
    
    async for thread in archive.archived_threads():
        print(thread.name, flush=True)
        channelsToDo = list(filter(lambda channel: channel.name != thread.name, channelsToDo))

    count = len(list(channelsToDo))
    await ctx.channel.send(f"I believe {count} channels (out of the {ogCount} associated with this season) are not archived. However, I am not sure all of the threats I went through are complete, so I suggest you check them out yourself ;)") 
    await ctx.followup.send(f"Games not archived: {count}/{ogCount}")

    

@bot.slash_command(name="archive_season", guild_ids=GUILD, description="Archive all games from a given season")
async def archive_season(ctx, name: Option(str, "enter season number please")):
    await ctx.defer(ephemeral=True)
    
    if not await hasPermissions(ctx): return

    archive = None
    channelsToDo = []
    for channel in ctx.guild.text_channels:
        if channel.name == "archive-season-"+name:
            archive = channel
        if channel.name[1:2+len(name)] == "s"+name :
            print(f"selected {channel.name}")
            channelsToDo.append(channel)
    
    if archive == None:
        archive = await createChannel(ctx, "archive-season-" + name)
   
    for thread in archive.threads:
        channelsToDo = list(filter(lambda channel: channel.name != thread.name, channelsToDo))
    
    print("creating:",channelsToDo)

    async def fuckUpAChannel(ctx, channel):
        try:    
            await moveChannelIntoAThread(ctx, channel, archive, channel.name)
        except Exception as e:
            print(e)
   
    await asyncio.gather(*[fuckUpAChannel(ctx, channel) for channel in channelsToDo])
    
    
    await ctx.followup.send("done")
    

@bot.slash_command(name="speak", guild_ids=GUILD, description="Behold!")
async def speak(ctx, message: Option(str, "speak, my child!")):
    await ctx.defer(ephemeral=True)
    await ctx.channel.send(message)
    await ctx.followup.send("done")

@bot.slash_command(name="change_my_color", guild_ids=GUILD, description="Remove a channel")
async def recolorMe(ctx, role: Option(discord.Role, "select a role"), r: Option(int, "Select a channel to remove"), g: Option(int, "Select a channel to remove"), b: Option(int, "Select a channel to remove")):
    await ctx.defer(ephemeral=True)
    
    if not await hasPermissions(ctx): return

    await role.edit(colour=discord.Color.from_rgb(r,g,b))
    await ctx.followup.send("done")

@bot.slash_command(name="dump_role", guild_ids=GUILD, description="Dump all players by assigned team")
async def dump_role(ctx, role: discord.Role):
    await ctx.defer(ephemeral=True)
    ctx.followup.send(f"DUMPING ROLE {str(role)}")
    for member in role.members:
        ctx.followup.send(str(member))


@bot.slash_command(name="channel_to_thread", guild_ids=GUILD, description="Convert a channel to a thread with the"
                                                                    "option to remove the original channel")
async def channel_to_thread(ctx, channel: Option(discord.TextChannel, "Select a channel to turn into a thread"),
                            place: Option(discord.TextChannel, "Select a channel to create the thread in"),
                            name: Option(str, "Enter a name for the thread [Default: Channel Name]",
                                         required=False)):

    await ctx.defer(ephemeral=True)

    if not await hasPermissions(ctx): return

    await ctx.followup.send(f"transfering channel: {channel.name}")

    await moveChannelIntoAThread(ctx, channel, place, name)
    
    await ctx.followup.send(f"done")





@bot.event
async def on_ready():
    bot.add_view(btn_createThread())
    print(f"Logged in as {bot.user}")
    print(f"Creating invite link: https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}"
          f"&permissions=395942423568&scope=bot%20applications.commands")


class btn_createThread(View, discord.TextChannel):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Create new thread", style=ButtonStyle.green, emoji="���", custom_id=f"button_newThread")
    async def button_callback(self, button, interaction):
        modal = ThreadModal(title="New Thread", custom_id=f"threadModal_newThread")
        await interaction.response.send_modal(modal)


bot.run(TOKEN)

