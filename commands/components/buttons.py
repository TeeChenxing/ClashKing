
import disnake
import inspect

from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from utility.discord_utils import registered_functions


async def button_logic(button_data: str, bot: CustomClient, guild: disnake.Guild, ctx: disnake.MessageInteraction = None):
    split_data = button_data.split(":")
    lookup_name = button_data.split(":")[0]
    function, parser, ephemeral, no_embed = registered_functions.get(lookup_name)
    if function is None:
        return None #maybe change this
    if ctx:
        await ctx.response.defer(ephemeral=ephemeral)

    parser_split = parser.split(":")
    hold_kwargs = {"bot": bot, "server": guild}
    for data, name in zip(split_data[1:], parser_split[1:]):
        if data.isdigit():
            data = int(data)
        if name == "server":
            if data == guild.id:
                continue
            else:
                data = await bot.getch_guild(data)
        if data == "None":
            data = None
        if name == "clan":
            data = await bot.getClan(clan_tag=data)
        elif name == "ctx":
            data = ctx
        elif name == "player":
            data = await bot.getPlayer(player_tag=data)
        hold_kwargs[name] = data

    server = hold_kwargs.get("server")
    embed_color = await bot.ck_client.get_server_embed_color(server_id=server.id)
    hold_kwargs["embed_color"] = embed_color
    hold_kwargs = {key: hold_kwargs[key] for key in inspect.getfullargspec(function).args}
    embed = await function(**hold_kwargs)
    if no_embed:
        return None
    return embed


class ButtonHandler(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        button_data = ctx.data.custom_id
        if ":" not in button_data:
            return

        embed = await button_logic(button_data=button_data, bot=self.bot, ctx=ctx, guild=ctx.guild)

        #in some cases the handling is done outside this function
        if embed is None:
            return

        if isinstance(embed, list):
            await ctx.edit_original_message(embeds=embed)
        else:
            await ctx.edit_original_message(embed=embed)

def setup(bot):
    bot.add_cog(ButtonHandler(bot))


