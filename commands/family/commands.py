import coc
import disnake
import calendar
import pytz
import uuid
from utility.clash.capital import gen_raid_weekend_datestrings, get_raidlog_entry
from CustomClasses.CustomBot import CustomClient
from disnake.ext import commands
from typing import List
#from ImageGen import ClanCapitalResult as capital_gen
from utility.constants import EMBED_COLOR
from utility.components import clan_board_components
from CustomClasses.CustomPlayer import MyCustomPlayer

from discord import convert, autocomplete, options
from .utils import family_composition, family_summary


class FamilyCommands(commands.Cog, name="Family Commands"):

    def __init__(self, bot: CustomClient):
        self.bot = bot


    @commands.slash_command(name="family")
    async def family(self, ctx: disnake.ApplicationCommandInteraction):
        result = await self.bot.user_settings.find_one({"discord_user" : ctx.author.id})
        ephemeral = False
        if result is not None:
            ephemeral = result.get("private_mode", False)
        if "board" in ctx.filled_options.keys():
            ephemeral = True
        await ctx.response.defer(ephemeral=ephemeral)


    @family.sub_command(name="compo", description="Composition of values in a family")
    async def family_compo(self, ctx: disnake.ApplicationCommandInteraction,
                         type_: str = commands.Param(name="type", default="Townhall", choices=["Townhall", "Trophies", "Location", "Role",  "League"]),
                         server: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server)):
        server = server or ctx.guild
        server_result = await self.bot.server_db.find_one({"server" : server.id})
        embed = await family_composition(bot=self.bot, server=server, type=type_, embed_color=disnake.Color(server_result.get("embed_color", EMBED_COLOR)))
        custom_id = f"family_{uuid.uuid4()}"
        buttons = disnake.ui.ActionRow(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=custom_id))
        await ctx.edit_original_response(embed=embed, components=[buttons])
        as_dict = {
            "button_id": custom_id,
            "command": "family compo",
            "server": server.id,
            "type" : type_,
            "fields" : ["type", "server"]
        }
        await self.bot.button_store.insert_one(as_dict)


    @family.sub_command(name="summary", description="Summary of stats for a family")
    async def summary(self, ctx: disnake.ApplicationCommandInteraction,
                      season: str = options.optional_season,
                      limit: int = commands.Param(default=5, min_value=1, max_value=15),
                      server: disnake.Guild = commands.Param(converter=convert.server, default=None, autocomplete=autocomplete.server)
                      ):

        server = server or ctx.guild
        embed_color = await self.bot.ck_client.get_server_embed_color(server_id=server.id)
        embeds = await family_summary(bot=self.bot, server=server, limit=limit, season=season, embed_color=embed_color)
        buttons = disnake.ui.ActionRow()
        buttons.add_button(
            label="", emoji=self.bot.emoji.refresh.partial_emoji,
            style=disnake.ButtonStyle.grey,
            custom_id=f"familysummary:{server.id}:{season}:{limit}")
        await ctx.edit_original_message(embeds=embeds, components=[buttons])


def setup(bot):
    bot.add_cog(FamilyCommands(bot))

