import disnake

from disnake.ext import commands
from main import check_commands
from CustomClasses.CustomBot import CustomClient
from CustomClasses.CustomServer import CustomServer
from Utils.constants import DEFAULT_EVAL_ROLE_TYPES
from Utils.discord_utils import interaction_handler
from Exceptions.CustomExceptions import MessageException
from Utils.components import create_components
from Discord import convert
from .utils import logic



class eval(commands.Cog, name="Eval"):
    """A couple of simple commands."""

    def __init__(self, bot: CustomClient):
        self.bot = bot

    @commands.slash_command(name="refresh", description="Refresh roles for a user, users in a role, or yourself (no arguments)")
    async def refresh(self, ctx: disnake.ApplicationCommandInteraction,
                   role_or_user: disnake.Role | disnake.Member = None,
                   test: bool = commands.Param(default=False, converter=convert.basic_bool, choices=["Yes", "No"]),
                   advanced_mode: bool = commands.Param(default=False, converter=convert.basic_bool, choices=["Yes", "No"])
                   ):
        """
            Parameters
            ----------
            role_or_user: (optional) role or user to refresh roles for
            test: (optional) test mode, won't make any changes
            advanced_mode: (optional) choose what role types to evaluate
        """

        await ctx.response.defer()
        if role_or_user is None:
            role_or_user = ctx.user
        else:
            perms = await self.bot.white_list_check(ctx=ctx, command_name="refresh")
            if not perms and not ctx.author.guild_permissions.manage_guild:
                raise MessageException("Missing Manage Server Permissions and/or not whitelisted for this command (`/whitelist add`")

        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild_id)
        if advanced_mode:
            options = []
            for option in DEFAULT_EVAL_ROLE_TYPES:
                value = option
                option = option.capitalize()
                if option == "Not_family":
                    option = "Not Family"
                options.append(disnake.SelectOption(label=option, value=value))

            select = disnake.ui.Select(
                options=options,
                placeholder="Eval Options",
                # the placeholder text to show when no options have been chosen
                min_values=1,  # the minimum number of options a user must select
                max_values=len(options),  # the maximum number of options a user can select
            )
            dropdown = [disnake.ui.ActionRow(select)]
            embed = disnake.Embed(description="**Choose which role types you would like to eval:**", color=db_server.embed_color)
            await ctx.edit_original_message(embed=embed, components=dropdown)
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx)
            eval_types = res.values
            embed = disnake.Embed(description="**<a:loading:948121999526461440>Role Refresh In Progress**", color=db_server.embed_color)
            await res.edit_original_message(embed=embed, components=[])
        else:
            eval_types = DEFAULT_EVAL_ROLE_TYPES



        if isinstance(role_or_user, disnake.Role):
            members = await ctx.guild.getch_members([m.id for m in role_or_user.members])
            clans = await self.bot.clan_db.distinct("tag", filter={"generalRole": role_or_user.id})
            if not clans:
                result = await self.bot.generalfamroles.find_one({"role": role_or_user.id})
                if result:
                    clans = await self.bot.clan_db.distinct("tag", {"server": ctx.guild.id})

            if clans:
                clans = await self.bot.get_clans(tags=clans)
                embed = disnake.Embed(
                    description="<a:loading:884400064313819146> Adding current clan members to refresh...",
                    color=db_server.embed_color)
                await ctx.edit_original_message(embed=embed)
                clan_members = [member.tag for clan in clans for member in clan.members]
                get_links = await self.bot.link_client.get_links(*clan_members)
                discord_ids = [_id for tag, _id in get_links]
                fetched_members = await ctx.guild.getch_members(discord_ids)
                members = members + [m for m in fetched_members if m not in members]
        else:
            members = await ctx.guild.getch_members([role_or_user.id])

        if not members:
            raise MessageException("No Members Found")
        elif len(members) > 1000:
            raise MessageException(f"Max 1000 members can be refreshed at a time ({len(members)} members attempted)")

        embeds = await logic(bot=self.bot, guild=ctx.guild, db_server=db_server, members=members, role_or_user=role_or_user, eval_types=eval_types, test=test)

        await ctx.edit_original_message(embeds=embeds[:1])

        current_page = 0
        await ctx.edit_original_message(embed=embeds[0], components=create_components(current_page, embeds, True))


        while True:
            res: disnake.MessageInteraction = await interaction_handler(bot=self.bot, ctx=ctx, timeout=3600)

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




    @commands.slash_command(name="autoeval")
    async def autoeval(self, ctx):
        pass


    @autoeval.sub_command(name="blacklist-roles", description="Set blacklisted roles in autoeval (people with these roles will not be autoevaled)")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def auto_eval_blacklist(self, ctx: disnake.ApplicationCommandInteraction, add: disnake.Role = None, remove: disnake.Role = None):
        await ctx.response.defer()
        db_server = await self.bot.get_custom_server(guild_id=ctx.guild.id)
        if add is None and remove is None:
            text = ""
            for role in db_server.blacklisted_roles:
                real_role = ctx.guild.get_role(role)
                if real_role is None:
                    continue
                text += f"- {real_role.mention}\n"
            if text == "":
                text = "No Blacklisted Roles"
            embed = disnake.Embed(title=f"{ctx.guild.name} AutoEval Blacklisted Roles",description=text, color=disnake.Color.green())
            return await ctx.edit_original_message(embed=embed)

        if add is not None and remove is not None:
            raise MessageException("Cannot both remove and add blacklist roles at the same time")

        if add is not None:
            if add.id in db_server.blacklisted_roles:
                raise MessageException(f"{add.mention} is already in the autoeval blacklisted roles.")
            await db_server.add_blacklisted_role(id=add.id)
            embed = disnake.Embed(description=f"{add.mention} added to autoeval blacklisted roles", color=disnake.Color.green())
            return await ctx.edit_original_message(embed=embed)

        if remove is not None:
            if remove.id not in db_server.blacklisted_roles:
                raise MessageException(f"{remove.mention} is not in the autoeval blacklisted roles.")
            await db_server.remove_blacklisted_role(id=remove.id)
            embed = disnake.Embed(description=f"{remove.mention} removed from autoeval blacklisted roles", color=disnake.Color.green())
            return await ctx.edit_original_message(embed=embed)



    @autoeval.sub_command(name="options", description="Set settings for autoeval")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def auto_eval_options(self, ctx: disnake.ApplicationCommandInteraction,
                                role_treatment: str = commands.Param(default=None, choices=["Add", "Remove", "Both"]),
                                nickname_change: str = commands.Param(default=None, choices=["True", "False"]),
                                blacklist_role_add: disnake.Role = None,
                                blacklist_role_remove: disnake.Role = None):
        await ctx.response.defer()
        if blacklist_role_add.id == blacklist_role_remove.id:
            raise MessageException("Cannot both remove and add the same role to/from blacklist at the same time")

        db_server = await self.bot.get_custom_server(guild_id=ctx.guild.id)
        changed_text = ""
        if role_treatment is not None:
            if role_treatment == "Both":
                choices = ["Add", "Remove"]
            else:
                choices = [role_treatment]
            await db_server.set_role_treatment(treatment=choices)
            changed_text += f"- **Role Treatment:** {choices}\n"

        if nickname_change is not None:
            await db_server.set_auto_eval_nickname(nickname_change == "True")
            changed_text += f"- **Nickname Change:** {nickname_change}\n"

        if blacklist_role_add is not None:
            if blacklist_role_add.id in db_server.blacklisted_roles:
                raise MessageException(f"{blacklist_role_add.mention} is already in the autoeval blacklisted roles.")
            await db_server.add_blacklisted_role(id=blacklist_role_add.id)
            changed_text += f"- **BlackList Role Add:** {blacklist_role_add.mention}\n"

        if blacklist_role_remove is not None:
            if blacklist_role_remove.id not in db_server.blacklisted_roles:
                raise MessageException(f"{blacklist_role_remove.mention} is not in the autoeval blacklisted roles.")
            await db_server.remove_blacklisted_role(id=blacklist_role_remove.id)
            changed_text += f"- **BlackList Role Removed:** {blacklist_role_remove.mention}\n"

        if changed_text == "":
            changed_text = "No Changes Made!"

        embed = disnake.Embed(title=f"{ctx.guild.name} AutoEval Settings Changed", description=changed_text, color=db_server.embed_color)
        if ctx.guild.icon is not None:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.edit_original_message(embed=embed)




    @autoeval.sub_command(name="triggers", description="Set triggers for autoeval")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def auto_eval_options(self, ctx: disnake.ApplicationCommandInteraction):
        pass



    #SETTINGS
    @commands.slash_command(name="family-roles")
    async def family_roles(self, ctx):
        pass

    @commands.slash_command(name="townhall-roles")
    async def townhall_roles(self, ctx):
        pass

    @commands.slash_command(name="league-roles")
    async def league_roles(self, ctx):
        pass

    @commands.slash_command(name="builderhall-roles")
    async def builderhall_roles(self, ctx):
        pass

    @commands.slash_command(name="builder-league-roles")
    async def builder_league_roles(self, ctx):
        pass

    @commands.slash_command(name="achievement-roles")
    async def achievement_roles(self, ctx):
        pass

    @commands.slash_command(name="status-roles")
    async def status_roles(self, ctx):
        pass

    '''@eval.sub_command(name="role-list", description="List of eval affiliated roles for this server")
    async def eval_role_list(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()

        family_roles = await self.bot.generalfamroles.find({"server": ctx.guild.id}).to_list(length=100)
        not_family_roles = await self.bot.notfamroles.find({"server": ctx.guild.id}).to_list(length=100)
        ignored_roles = await self.bot.ignoredroles.find({"server": ctx.guild.id}).to_list(length=100)

        list_roles = [family_roles, not_family_roles, ignored_roles]
        role_names = ["Only-Family Roles", "Not-Family Roles", "Ignored Roles"]

        embed = disnake.Embed(title=f"{ctx.guild.name} Family Role List", color=disnake.Color.green())
        for role_list, role_name in zip(list_roles, role_names):
            text = ""
            for result in role_list:
                role = ctx.guild.get_role(result.get("role"))
                if role is None:
                    continue
                text += f"{role.mention}\n"
            if text == "":
                text = "No Roles"
            embed.add_field(name=f"**{role_name}**", value=text)

        list_ths = ""
        all = await self.bot.townhallroles.find({"server": ctx.guild.id}).to_list(length=None)
        all = sorted(all, key= lambda x : int(x.get("th")[2:]))
        for role in all:
            roleid = role.get("role")
            th = role.get("th")
            list_ths += f"{th.capitalize()}: <@&{roleid}>\n"

        if list_ths == "":
            list_ths = "None Set"
        embed.add_field(name=f"**Townhall Roles**", value=list_ths)

        list_ths = ""
        all = await self.bot.builderhallroles.find({"server": ctx.guild.id}).to_list(length=None)
        all = sorted(all, key=lambda x: int(x.get("bh")[2:]))
        for role in all:
            roleid = role.get("role")
            th = role.get("bh")
            list_ths += f"{th.capitalize()}: <@&{roleid}>\n"

        if list_ths == "":
            list_ths = "None Set"
        embed.add_field(name=f"**Builderhall Roles**", value=list_ths)

        list = ""
        all = await self.bot.legendleagueroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**League & Trophy Roles**", value=list)

        list = ""
        all = await self.bot.builderleagueroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**Builder League Roles**", value=list)


        list = ""
        all = await self.bot.statusroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**Status Roles**", value=list)

        list = ""
        all = await self.bot.achievementroles.find({"server": ctx.guild.id}).to_list(length=None)
        for role in all:
            roleid = role.get("role")
            type = role.get("type")
            type = type.split("_")[0].capitalize() + " " + type.split("_")[1].capitalize()
            list += f"{type}: <@&{roleid}>\n"

        if list == "":
            list = "None Set"
        embed.add_field(name=f"**Achievement Roles**", value=list)

        await ctx.edit_original_message(embed=embed)


    @eval.sub_command(name="role-remove", description="Remove an eval affiliated role")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def eval_role_remove(self, ctx: disnake.ApplicationCommandInteraction,
                               townhall: str = commands.Param(default=None, choices=["th7", "th8", "th9", "th10", "th11", "th12", "th13", "th14", "th15"]),
                               builderhall: str = commands.Param(default=None, choices=["bh3", "bh4", "bh5", "bh6", "bh7", "bh8", "bh9", "bh10"]),
                               league_role: str = commands.Param(default=None,
                                   choices=["bronze_league", "silver_league", "gold_league", "crystal_league",
                                            "master_league", "champion_league", "titan_league",
                                            "legends_league", "trophies_5500", "trophies_5700", "trophies_6000"]),
                               builder_league: str = commands.Param(default=None, choices=["wood_league", "clay_league", "stone_league", "copper_league", "brass_league", "iron_league",
                                        "steel_league", "titanium_league", "platinum_league", "emerald_league", "ruby_league", "diamond_league"]),
                               achievement_roles: str = commands.Param(default=None, choices=["donos_10000", "donos_25000", "top_donator_last_season", "top_donator_ongoing_season"])
                               ):
        await ctx.response.defer()

        role_types = [townhall, builderhall, league_role, builder_league, achievement_roles]
        if role_types.count(None) == len(role_types):
            return await ctx.send("Must provide at least one role type to remove!")

        removed_text = ""
        if townhall:
            results = await self.bot.townhallroles.find_one({"$and": [
                {"th": f"{townhall}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That townhall does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.townhallroles.find_one_and_delete({"$and": [
                    {"th": f"{townhall}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{townhall.capitalize()} eval role removed - <@&{mention}>\n"

        if builderhall:
            results = await self.bot.builderhallroles.find_one({"$and": [
                {"th": f"{builderhall}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That builderhall does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.builderhallroles.find_one_and_delete({"$and": [
                    {"th": f"{builderhall}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{builderhall.capitalize()} eval role removed - <@&{mention}>\n"

        if league_role:
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"type": f"{league_role}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That league role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.legendleagueroles.find_one_and_delete({"$and": [
                    {"type": f"{league_role}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{league_role} eval role removed - <@&{mention}>\n"

        if builder_league:
            results = await self.bot.builderleagueroles.find_one({"$and": [
                {"type": f"{builder_league}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That league role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.builderleagueroles.find_one_and_delete({"$and": [
                    {"type": f"{builder_league}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{builder_league} eval role removed - <@&{mention}>\n"

        if status_roles:
            results = await self.bot.statusroles.find_one({"$and": [
                {"type": f"{status_roles}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That status role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.statusroles.find_one_and_delete({"$and": [
                    {"type": f"{status_roles}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{status_roles} eval role removed - <@&{mention}>\n"

        if achievement_roles:
            results = await self.bot.statusroles.find_one({"$and": [
                {"type": f"{achievement_roles}"},
                {"server": ctx.guild.id}
            ]})
            if results is None:
                return await ctx.send("That achievement role type does not have a role assigned to it for eval currently.")
            else:
                mention = results.get("role")
                await self.bot.statusroles.find_one_and_delete({"$and": [
                    {"type": f"{achievement_roles}"},
                    {"server": ctx.guild.id}
                ]})

            removed_text += f"{achievement_roles} eval role removed - <@&{mention}>\n"

        embed = disnake.Embed(title="Eval Role Removals", description=removed_text, color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)'''



    @family_roles.sub_command(name="add", description="Add Family Based Eval Roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def family_roles_add(self, ctx: disnake.ApplicationCommandInteraction,
                               type:str = commands.Param(choices=["Only-Family Roles", "Family Exclusive Roles", "Not-Family Roles", "Ignored Roles"]),
                               role: disnake.Role = commands.Param(name="role")):

        await ctx.response.defer()
        if type == "Only-Family Roles":
            database = self.bot.generalfamroles
        elif type == "Family Exclusive Roles":
            database = self.bot.familyexclusiveroles
        elif type == "Not-Family Roles":
            database = self.bot.notfamroles
        elif type == "Ignored Roles":
            database = self.bot.ignoredroles

        embed = await self.family_role_add(database=database, role=role, guild=ctx.guild, type=type)

        await ctx.edit_original_message(embed=embed)


    @family_roles.sub_command(name="remove", description="Remove Family Based Eval Roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def family_roles_remove(self, ctx: disnake.ApplicationCommandInteraction,
                                  type: str = commands.Param(choices=["Only-Family Roles", "Family Exclusive Roles", "Not-Family Roles", "Ignored Roles"]),
                                  role: disnake.Role = commands.Param(name="role")):

        await ctx.response.defer()
        if type == "Only-Family Roles":
            database = self.bot.generalfamroles
        elif type == "Family Exclusive Roles":
            database = self.bot.familyexclusiveroles
        elif type == "Not-Family Roles":
            database = self.bot.notfamroles
        elif type == "Ignored Roles":
            database = self.bot.ignoredroles

        embed = await self.family_role_remove(database=database, role=role, guild=ctx.guild, type=type)
        await ctx.edit_original_message(embed=embed)

    async def family_role_add(self, database, type: str, role: disnake.Role, guild: disnake.Guild) -> disnake.Embed:
        results = await database.find_one({"$and": [
            {"role": role.id},
            {"server": guild.id}
        ]})
        if results is not None:
            return disnake.Embed(description=f"{role.mention} is already in the {type} list.",
                                 color=disnake.Color.red())

        if role.is_default():
            return disnake.Embed(description=f"Cannot use the @everyone role for {type}", color=disnake.Color.red())

        await database.insert_one({
            "server": guild.id,
            "role": role.id
        })

        embed = disnake.Embed(
            description=f"{role.mention} added to the {type} list.",
            color=disnake.Color.green())
        return embed

    async def family_role_remove(self, database, type: str, role: disnake.Role, guild: disnake.Guild) -> disnake.Embed:
        results = await database.find_one({"$and": [
            {"role": role.id},
            {"server": guild.id}
        ]})
        if results is None:
            return disnake.Embed(description=f"{role.mention} is not currently in the {type} list.",
                                 color=disnake.Color.red())

        if role.is_default():
            return disnake.Embed(description=f"Cannot use the @everyone role for {type}", color=disnake.Color.red())

        await database.find_one_and_delete({"role": role.id})

        return disnake.Embed(description=f"{role.mention} removed from the {type} list.", color=disnake.Color.green())



    ###Townhall Roles Section
    @townhall_roles.sub_command(name="set", description="Sets roles to add for townhall levels 7 and up")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def townhall_roles_set(self, ctx: disnake.ApplicationCommandInteraction, th7: disnake.Role = None,
                                 th8: disnake.Role = None, th9: disnake.Role = None,
                                 th10: disnake.Role = None, th11: disnake.Role = None, th12: disnake.Role = None,
                                 th13: disnake.Role = None, th14: disnake.Role = None, th15: disnake.Role = None):

        if th7 is None and th8 is None and th9 is None and th10 is None and th11 is None and th12 is None and th13 is None and th14 is None and th15 is None:
            return await ctx.send("Please provide a role for at least 1 townhall level.")

        roles_updated = ""

        if th7 is not None:
            roles_updated += f"TH7: {th7.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th7.id},
                {"th": "th7"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th7.id,
                     "th": "th7",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th7"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th7.id}})
        if th8 is not None:
            roles_updated += f"TH8: {th8.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th8.id},
                {"th": "th8"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th8.id,
                     "th": "th8",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th8"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th8.id}})
        if th9 is not None:
            roles_updated += f"TH9: {th9.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th9.id},
                {"th": "th9"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th9.id,
                     "th": "th9",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th9"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th9.id}})
        if th10 is not None:
            roles_updated += f"TH10: {th10.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th10.id},
                {"th": "th10"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th10.id,
                     "th": "th10",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th10"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th10.id}})
        if th11 is not None:
            roles_updated += f"TH11: {th11.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th11.id},
                {"th": "th11"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th11.id,
                     "th": "th11",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th11"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th11.id}})
        if th12 is not None:
            roles_updated += f"TH12: {th12.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th12.id},
                {"th": "th12"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th12.id,
                     "th": "th12",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th12"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th12.id}})
        if th13 is not None:
            roles_updated += f"TH13: {th13.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th13.id},
                {"th": "th13"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th13.id,
                     "th": "th13",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th13"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th13.id}})
        if th14 is not None:
            roles_updated += f"TH14: {th14.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th14.id},
                {"th": "th14"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th14.id,
                     "th": "th14",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th14"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th14.id}})
        if th15 is not None:
            roles_updated += f"TH15: {th15.mention}\n"
            results = await self.bot.townhallroles.find_one({"$and": [
                {"role": th15.id},
                {"th": "th15"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.townhallroles.insert_one(
                    {"role": th15.id,
                     "th": "th15",
                     "server": ctx.guild.id})
            else:
                await self.bot.townhallroles.update_one({"$and": [
                    {"th": "th15"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": th15.id}})

        embed = disnake.Embed(title="**Townhall Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)


    ###Builderhall Roles Section
    @builderhall_roles.sub_command(name="set", description="Sets roles to add for builderhall levels 3 and up")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def builderhall_roles_set(self, ctx: disnake.ApplicationCommandInteraction, bh3: disnake.Role = None,
                                    bh4: disnake.Role = None, bh5: disnake.Role = None,
                                    bh6: disnake.Role = None, bh7: disnake.Role = None, bh8: disnake.Role = None,
                                    bh9: disnake.Role = None, bh10: disnake.Role = None):

        perms = ctx.author.guild_permissions.manage_guild
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Server` permissions.",
                                  color=disnake.Color.red())
            return await ctx.send(embed=embed)

        if bh3 is None and bh4 is None and bh5 is None and bh6 is None and bh7 is None and bh8 is None and bh9 is None and bh10 is None:
            return await ctx.send("Please provide a role for at least 1 builderhall level.")

        roles_updated = ""

        spot_to_text = ["bh3", "bh4", "bh5", "bh6", "bh7", "bh8", "bh9", "bh10"]
        list_roles = [bh3, bh4, bh5, bh6, bh7, bh8, bh9, bh10]

        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text.upper()}: {role.mention}\n"
            results = await self.bot.builderhallroles.find_one({"$and": [
                {"role": role.id},
                {"bh": f"{role_text}"},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.builderhallroles.insert_one(
                    {"role": role.id,
                     "bh": f"{role_text}",
                     "server": ctx.guild.id})
            else:
                await self.bot.builderhallroles.update_one({"$and": [
                    {"bh": f"{role_text}"},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**Builderhall Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)


    ###League Roles Section
    @league_roles.sub_command(name="set", description="Sets roles to add for leagues")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def league_roles_set(self, ctx: disnake.ApplicationCommandInteraction, bronze_league: disnake.Role = None,
                               silver_league: disnake.Role = None, gold_league: disnake.Role = None,
                               crystal_league: disnake.Role = None, master_league: disnake.Role = None,
                               champion_league: disnake.Role = None, titan_league: disnake.Role = None,
                               legends_league: disnake.Role = None, trophies_5500: disnake.Role = None,
                               trophies_5700: disnake.Role = None, trophies_6000: disnake.Role = None):

        list_roles = [bronze_league, silver_league, gold_league, crystal_league, master_league, champion_league,
                      titan_league, legends_league, trophies_5500, trophies_5700, trophies_6000]

        if len(set(list_roles)) == 1:
            await ctx.send("Please select at least one role to set.")

        spot_to_text = ["bronze_league", "silver_league", "gold_league", "crystal_league", "master_league",
                        "champion_league",
                        "titan_league", "legends_league", "trophies_5500", "trophies_5700", "trophies_6000"]

        roles_updated = ""
        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text}: {role.mention}\n"
            results = await self.bot.legendleagueroles.find_one({"$and": [
                {"role": role.id},
                {"type": role_text},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.legendleagueroles.insert_one(
                    {"role": role.id,
                     "type": role_text,
                     "server": ctx.guild.id})
            else:
                await self.bot.legendleagueroles.update_one({"$and": [
                    {"type": role_text},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**League Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)



    @builder_league_roles.sub_command(name="set", description="Sets roles to add for builder leagues")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def builder_league_roles_set(self, ctx: disnake.ApplicationCommandInteraction, wood_league: disnake.Role = None,
                               clay_league: disnake.Role = None, stone_league: disnake.Role = None,
                               copper_league: disnake.Role = None, brass_league: disnake.Role = None,
                               iron_league: disnake.Role = None, steel_league: disnake.Role = None,
                               titanium_league: disnake.Role = None, platinum_league: disnake.Role = None,
                               emerald_league: disnake.Role = None, ruby_league: disnake.Role = None, diamond_league: disnake.Role = None):

        list_roles = [wood_league, clay_league, stone_league, copper_league, brass_league, iron_league,
                      steel_league, titanium_league, platinum_league, emerald_league, ruby_league, diamond_league]

        if list_roles.count(None) == len(list_roles):
            return await ctx.send("Please select at least one role to set.")

        spot_to_text = ["wood_league", "clay_league", "stone_league", "copper_league", "brass_league",
                        "iron_league",
                        "steel_league", "titanium_league", "platinum_league", "emerald_league", "ruby_league", "diamond_league"]

        roles_updated = ""
        for count, role in enumerate(list_roles):
            if role is None:
                continue
            role_text = spot_to_text[count]
            roles_updated += f"{role_text}: {role.mention}\n"
            results = await self.bot.builderleagueroles.find_one({"$and": [
                {"role": role.id},
                {"type": role_text},
                {"server": ctx.guild.id}
            ]})

            if results is None:
                await self.bot.builderleagueroles.insert_one(
                    {"role": role.id,
                     "type": role_text,
                     "server": ctx.guild.id})
            else:
                await self.bot.builderleagueroles.update_one({"$and": [
                    {"type": role_text},
                    {"server": ctx.guild.id}
                ]}, {'$set': {"role": role.id}})

        embed = disnake.Embed(title="**Builder League Roles that were set:**",
                              description=roles_updated,
                              color=disnake.Color.green())
        return await ctx.send(embed=embed)


    @status_roles.sub_command(name="set", description="Longevity roles")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def status_roles_set(self, ctx: disnake.ApplicationCommandInteraction, months: int, role: disnake.Role):
        await ctx.response.defer()
        if role.is_default():
            raise MessageException(f"{role.mention} cannot be used as role.")

        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild.id)
        await db_server.add_status_role(months=months, role_id=role.id)



    @achievement_roles.sub_command(name="set", description="Set role for top donators/activity & more")
    @commands.check_any(commands.has_permissions(manage_guild=True), check_commands())
    async def achievement_roles_set(self, ctx: disnake.ApplicationCommandInteraction,
                                    type: str = commands.Param(choices=["Donation", "Trophies", "Activity", "Total Looted"]),
                                    amount_or_rank: int = commands.Param(),
                                    season: str = commands.Param(choices=["Current Season", "Previous Season"]),
                                    apply_scope: str = commands.Param(default="Family", choices=["Family", "Clan", "Both"])):
        await ctx.response.defer()
        db_server = await self.bot.ck_client.get_server_settings(server_id=ctx.guild.id)
        is_rank = (amount_or_rank <= 100)
        await db_server.add_achievement_role(type=type.lower().replace(" ", "_"), amount=amount_or_rank,
                                             season=season.lower().replace(" ", "_"), scope=apply_scope.lower())






    @commands.user_command(name="Nickname", description="Change nickname of a user")
    async def auto_nick(self, ctx: disnake.ApplicationCommandInteraction, user: disnake.User):
        await ctx.response.defer(ephemeral=True)
        perms = ctx.author.guild_permissions.manage_nicknames
        if user.id == ctx.author.id:
            perms = True
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Nickname` permissions.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        try:
            member = await ctx.guild.fetch_member(user.id)
        except:
            member = None
        if member is None:
            return await ctx.edit_original_message(f"{user.name} [{user.mention}] is not a member of this server.")

        account_tags = await self.bot.get_tags(user.id)
        abbreviations = {}
        clan_tags = []
        for role in await self.bot.clan_db.find({"server": ctx.guild.id}).to_list(length=200):
            clan_tags.append(role.get("tag"))
            clan_abbreviation = role.get("abbreviation")
            abbreviations[role.get("tag")] = clan_abbreviation

        GLOBAL_IS_FAMILY = False
        abbreviations_to_have = []
        player_accounts = await self.bot.get_players(tags=account_tags, custom=False, use_cache=False)
        if len(player_accounts) == 0:
            return await ctx.send(content=f"No accounts linked to {user.mention}")

        list_of_clans = []
        for player in player_accounts:
            # ignore the global if even one account is in family
            is_family_member = await is_in_family(player, clan_tags)
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if player.clan is not None:
                list_of_clans.append(player.clan.name)

            if not is_family_member:
                continue

            if abbreviations[player.clan.tag] is not None:
                abbreviations_to_have.append(abbreviations[player.clan.tag])

        list_of_clans = list(set(list_of_clans))
        abbreviations_to_have = list(set(abbreviations_to_have))

        server = CustomServer(guild=ctx.guild, bot=self.bot)
        family_label = await server.family_label
        if family_label == "":
            family_label = []
        else:
            family_label = [family_label]

        abbreviations = []
        if abbreviations_to_have != []:
            abbreviations.append(", ".join(abbreviations_to_have))


        label_list = abbreviations + family_label + list_of_clans
        label_list = list(set(label_list))[:25]
        if label_list == []:
            label_list.append(ctx.guild.name)

        options = []
        for label in label_list:
            options.append(disnake.SelectOption(label=f"{label}", value=f"label_{label}"))

        stat_select = disnake.ui.Select(options=options, placeholder="Nickname Labels", min_values=1, max_values=1)

        st = disnake.ui.ActionRow()
        st.append_item(stat_select)

        options = []
        player_accounts = sorted(player_accounts, key= lambda x : x.trophies, reverse=True)[:25]
        names_taken = set()
        for player in player_accounts:
            if player.name in names_taken:
                continue
            names_taken.add(player.name)
            options.append(disnake.SelectOption(label=f"{player.name}", value=f"{player.name}", emoji=self.bot.fetch_emoji(player.town_hall).partial_emoji))

        profile_select = disnake.ui.Select(options=options, placeholder="Account List", min_values=1,max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        all_components = [st2, st]

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        embed = disnake.Embed(description=f"Nickname change for {user.mention}")
        await ctx.edit_original_message(embed=embed, components=all_components)

        name_to_set = player_accounts[0].name
        label_to_set = ""

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if "label_" in res.values[0]:
                label = res.values[0].replace("label_", "")
                if label_to_set == f" | {label}":
                    label_to_set = ""
                else:
                    label_to_set = f" | {label}"
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(
                        content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.",
                        ephemeral=True)
            else:
                name_to_set = res.values[0]
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(
                        content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.",
                        ephemeral=True)


    '''@commands.slash_command(name="nickname", description="Change the nickname of a discord user")
    async def nickname(self, ctx: disnake.ApplicationCommandInteraction, user: disnake.User = None):
        await ctx.response.defer(ephemeral=True)
        if user is None:
            user = ctx.author
        perms = ctx.author.guild_permissions.manage_nicknames
        if user.id == ctx.author.id:
            perms = True
        if not perms:
            embed = disnake.Embed(description="Command requires you to have `Manage Nickname` permissions.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        try:
            member = await ctx.guild.fetch_member(user.id)
        except:
            member = None
        if member is None:
            return await ctx.edit_original_message(f"{user.name} [{user.mention}] is not a member of this server.")

        account_tags = await self.bot.get_tags(user.id)
        abbreviations = {}
        clan_tags = []
        for role in await self.bot.clan_db.find({"server": ctx.guild.id}).to_list(length=200):
            clan_tags.append(role.get("tag"))
            clan_abbreviation = role.get("abbreviation")
            abbreviations[role.get("tag")] = clan_abbreviation

        GLOBAL_IS_FAMILY = False
        abbreviations_to_have = []
        player_accounts = await self.bot.get_players(tags=account_tags, custom=False, use_cache=False)
        if len(player_accounts) == 0:
            return await ctx.send(content=f"No accounts linked to {user.mention}")

        list_of_clans = []
        for player in player_accounts:
            # ignore the global if even one account is in family
            is_family_member = await is_in_family(player, clan_tags)
            if not GLOBAL_IS_FAMILY:
                GLOBAL_IS_FAMILY = is_family_member

            if player.clan is not None:
                list_of_clans.append(player.clan.name)

            if not is_family_member:
                continue

            if abbreviations[player.clan.tag] is not None:
                abbreviations_to_have.append(abbreviations[player.clan.tag])

        list_of_clans = list(set(list_of_clans))
        abbreviations_to_have = list(set(abbreviations_to_have))

        server = CustomServer(guild=ctx.guild, bot=self.bot)
        family_label = await server.family_label
        if family_label == "":
            family_label = []
        else:
            family_label = [family_label]

        abbreviations = []
        if abbreviations_to_have != []:
            abbreviations.append(", ".join(abbreviations_to_have))

        label_list = abbreviations + family_label + list_of_clans
        label_list = list(set(label_list))[:25]
        if label_list == []:
            label_list.append(ctx.guild.name)

        options = []
        for label in label_list:
            options.append(disnake.SelectOption(label=f"{label}", value=f"label_{label}"))

        stat_select = disnake.ui.Select(options=options, placeholder="Nickname Labels", min_values=1, max_values=1)

        st = disnake.ui.ActionRow()
        st.append_item(stat_select)

        options = []
        player_accounts = sorted(player_accounts, key=lambda x: x.trophies, reverse=True)[:25]
        names_taken = set()
        for player in player_accounts:
            if player.name in names_taken:
                continue
            names_taken.add(player.name)
            options.append(disnake.SelectOption(label=f"{player.name}", value=f"{player.name}",
                                                emoji=self.bot.fetch_emoji(player.town_hall).partial_emoji))

        profile_select = disnake.ui.Select(options=options, placeholder="Account List", min_values=1, max_values=1)

        st2 = disnake.ui.ActionRow()
        st2.append_item(profile_select)

        all_components = [st2, st]

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        embed = disnake.Embed(description=f"Nickname change for {user.mention}")
        await ctx.edit_original_message(embed=embed, components=all_components)

        name_to_set = player_accounts[0].name
        label_to_set = ""

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                try:
                    await msg.edit(components=[])
                except:
                    pass
                break

            if "label_" in res.values[0]:
                label = res.values[0].replace("label_", "")
                if label_to_set == f" | {label}":
                    label_to_set = ""
                else:
                    label_to_set = f" | {label}"
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(
                        content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.",
                        ephemeral=True)
            else:
                name_to_set = res.values[0]
                try:
                    await member.edit(nick=f"{name_to_set}{label_to_set}")
                    await res.send(content=f"{member.mention} name changed.", ephemeral=True)
                except:
                    await res.send(
                        content=f"Could not edit {member.mention} name. Permissions error or user is above or equal to the bot's highest role.",
                        ephemeral=True)




    @eval_tag.autocomplete("player_tag")
    async def clan_player_tags(self, ctx: disnake.ApplicationCommandInteraction, query: str):
        names = await self.bot.family_names(query=query, guild=ctx.guild)
        return names'''




def setup(bot:  CustomClient):
    bot.add_cog(eval(bot))