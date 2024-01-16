import functools

import discord

from constants import ALLOWED_ROLES, ALLOWED_USERS, POLYELO_ID


def hasPermision(user: discord.Member):
    return True
    return user.id in ALLOWED_USERS or any(role.id in ALLOWED_ROLES for role in user.roles)

def onlyAuthorized(func):
    @functools.wraps(func)
    async def decorator(ctx: discord.ApplicationContext, *args, **kwargs):
        if hasPermision(ctx.author):
            await func(ctx, *args, **kwargs)
        else:
            await ctx.followup.send("permision denied!")

    return decorator

def onlyGameMembersAndAuthorized(func):
    @functools.wraps(func)
    async def decorator(ctx: discord.ApplicationContext, *args, **kwargs):
        firstMessage: discord.Message = ctx.channel.history(oldest_first=True, limit=1)[0]
        if (firstMessage.author == POLYELO_ID and ctx.author in firstMessage.mentions) or hasPermision(ctx.author):
            await func(ctx, *args, **kwargs)
        else:
            await ctx.followup.send("permision denied!")

    return decorator