import coc
import disnake
import uuid

from .utils import army_embed, super_troop_embed, clan_boost_embeds
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from utility.discord_utils import  interaction_handler
from utility.components import create_components
from utility.constants import  SUPER_TROOPS
from utility.cdn import upload_to_cdn
from discord import options

from .bbuttons import UtilityButtons

class UtilityCommands(UtilityButtons, commands.Cog, name="Utility"):

    def __init__(self, bot: CustomClient):
        super().__init__(bot)
        self.bot = bot

    @commands.slash_command(name='army', description="Create a visual message representation of an army link")
    async def army(self, ctx: disnake.ApplicationCommandInteraction,
                   link: str, nickname: str = "Results", clan_castle: str = "None"):
        """
            Parameters
            ----------
            link: an army link copied from in-game
            nickname: (optional) nickname for this army,
            clan_castle: (optional) clan castle to go with this army
        """
        embed = army_embed(bot=self.bot, nick=nickname, link=link, clan_castle=clan_castle)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label=f"Copy Link", emoji=self.bot.emoji.troop.partial_emoji, url=link))
        await ctx.send(embed=embed, components=buttons)



    @commands.slash_command(name="boosts", description="Get list of troops listed in a certain clan (or all family clans if blank)")
    async def super_troop_boosts(self, ctx: disnake.ApplicationCommandInteraction,
                                 clan: coc.Clan = options.optional_clan,
                                 super_troop=commands.Param(default=None, choices=SUPER_TROOPS)):
        """
            Parameters
            ----------
            clan: (optional) a clan
            super_troop: (optional) super troop to filter results for
        """
        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        if clan is None:
            clan_tags = [c.tag for c in db_server.clans]
            clans = await self.bot.get_clans(tags=clan_tags)
        else:
            clans = [clan]


        if super_troop is not None:
            embeds = await super_troop_embed(bot=self.bot, clans=clans, super_troop=super_troop, embed_color=db_server.embed_color)
        else:
            embeds = await clan_boost_embeds(bot=self.bot, clans=clans)

        if len(embeds) >= 2:
            await ctx.send(embed=embeds[0], components=create_components(0, embeds, True))
        else:
            custom_id = f"clan_{uuid.uuid4()}"
            components = disnake.ui.ActionRow()
            components.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=custom_id))
            as_dict = {
                "button_id": custom_id,
                "command": f"{ctx.application_command.qualified_name}",
                "clans": [c.tag for c in clans],
                "fields": ["clans"]
            }
            await self.bot.button_store.insert_one(as_dict)
            return await ctx.send(embeds=embeds, components=components)

        current_page = 0
        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, any_run=True)
            if res.data.custom_id == "Previous":
                current_page -= 1
                await res.edit_original_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Next":
                current_page += 1
                await res.edit_original_message(embed=embeds[current_page],
                                                components=create_components(current_page, embeds, True))

            elif res.data.custom_id == "Print":
                await res.delete_original_message()
                for embed in embeds:
                    await ctx.channel.send(embed=embed)


    @commands.slash_command(name="base")
    async def base(self, ctx: disnake.ApplicationCommandInteraction, base_link: str, description: str, photo: disnake.Attachment):
        if 'https://link.clashofclans.com/' and "=OpenLayout&id=" not in base_link:
            await ctx.response.defer(ephemeral=True)
            return await ctx.send("Not a valid base link")
        await ctx.response.defer()
        description = description[0:1900]
        description = description.replace("&&", "\n")

        r1 = disnake.ui.ActionRow()
        link_button = disnake.ui.Button(label="Link", emoji="🔗", style=disnake.ButtonStyle.green, custom_id="link")
        downloads = disnake.ui.Button(label="0 Downloads", emoji="📈", style=disnake.ButtonStyle.green, custom_id="who")
        r1.append_item(link_button)
        r1.append_item(downloads)

        r2 = disnake.ui.ActionRow()
        feedback = disnake.ui.Button(label="Feedback", emoji="💬", style=disnake.ButtonStyle.green,
                                     custom_id="feedback")
        feedback_button = disnake.ui.Button(label="Leave Feedback", emoji="📈", style=disnake.ButtonStyle.green,
                                            custom_id="leave")
        r2.append_item(feedback)
        r2.append_item(feedback_button)

        await upload_to_cdn(picture=photo)

        await ctx.edit_original_message(content=f"[➼](https://cdn.clashking.xyz/{photo.id}.png) {description}", components=[r1, r2])
        msg = await ctx.original_message()
        await self.bot.bases.insert_one({
            "link": base_link,
            "message_id": msg.id,
            "downloads": 0,
            "downloaders": [],
            "feedback": [],
            "new": True
        })



def setup(bot: CustomClient):
    bot.add_cog(UtilityCommands(bot))