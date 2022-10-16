import coc
import disnake
from disnake.ext import commands
from CustomClasses.CustomBot import CustomClient
from datetime import datetime
from utils.discord_utils import partial_emoji_gen
from utils.components import raid_buttons
from utils.clash import create_weekends, create_weekend_list, weekend_timestamps
import asyncio
from CustomClasses.CustomPlayer import MyCustomPlayer
import pandas as pd
from collections import defaultdict

class clan_commands(commands.Cog):

    def __init__(self, bot: CustomClient):
        self.bot = bot

    async def clan_converter(self, clan_tag: str):
        clan = await self.bot.getClan(clan_tag=clan_tag, raise_exceptions=True)
        if clan.member_count == 0:
            raise coc.errors.NotFound
        return clan

    @commands.slash_command(name="clan")
    async def clan(self, ctx):
        pass

    @clan.sub_command(name="search", description="lookup clan by tag")
    async def getclan(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Search by clan tag or select an option from the autocomplete
        """

        await ctx.response.defer()
        embed = disnake.Embed(
            description=f"<a:loading:884400064313819146> Fetching clan...",
            color=disnake.Color.green())
        await ctx.edit_original_message(embed=embed)

        embed = await self.clan_overview(ctx, clan)

        emoji = partial_emoji_gen(self.bot, "<:discord:840749695466864650>")
        rx = partial_emoji_gen(self.bot, "<:redtick:601900691312607242>")
        trophy = partial_emoji_gen(self.bot, "<:trophy:825563829705637889>")
        clan_e = partial_emoji_gen(self.bot, "<:clan_castle:855688168816377857>")
        opt = partial_emoji_gen(self.bot, "<:opt_in:944905885367537685>")
        stroop = partial_emoji_gen(self.bot, "<:stroop:961818095930978314>")
        cwl_emoji = partial_emoji_gen(self.bot, "<:cwlmedal:793561011801948160>")

        main = embed
        options = [  # the options in your dropdown
            disnake.SelectOption(label="Clan Overview", emoji=clan_e, value="clan"),
            disnake.SelectOption(label="Linked Players", emoji=emoji, value="link"),
            disnake.SelectOption(label="Unlinked Players", emoji=rx, value="unlink"),
            disnake.SelectOption(label="Players, Sorted: Trophies", emoji=trophy, value="trophies"),
            disnake.SelectOption(label="Players, Sorted: TH", emoji=self.bot.partial_emoji_gen(self.bot.fetch_emoji(14)), value="townhalls"),
            disnake.SelectOption(label="War Opt Statuses", emoji=opt, value="opt"),
            disnake.SelectOption(label="Super Troops", emoji=stroop, value="stroop"),
            disnake.SelectOption(label="CWL History", emoji=cwl_emoji, value="cwl")
        ]

        if clan.public_war_log:
            options.append(disnake.SelectOption(label="Warlog", emoji="ℹ️", value="warlog"))
        select = disnake.ui.Select(
            options=options,
            placeholder="Choose a page",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(embed=embed, components=dropdown)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

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

            await res.response.defer()

            if res.values[0] == "link":
                embed = await self.linked_players(ctx, clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "unlink":
                embed = await self.unlinked_players(ctx, clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "trophies":
                embed = await self.player_trophy_sort(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "townhalls":
                embed = await self.player_townhall_sort(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "clan":
                await res.edit_original_message(embed=main)
            elif res.values[0] == "opt":
                embed = await self.opt_status(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "warlog":
                embed = await self.war_log(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "stroop":
                embed = await self.stroop_list(clan)
                await res.edit_original_message(embed=embed)
            elif res.values[0] == "cwl":
                embed = await self.cwl_performance(clan)
                await res.edit_original_message(embed=embed)

    @clan.sub_command(name="player-links", description="List of un/linked players in clan")
    async def linked_clans(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed = await self.linked_players(ctx, clan)
        embed2 = await self.unlinked_players(ctx, clan)
        embed2.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"linked_{clan.tag}"))
        await ctx.edit_original_message(embeds=[embed, embed2], components=buttons)

    @clan.sub_command(name="sorted-trophies", description="List of clan members, sorted by trophies")
    async def player_trophy(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed = await self.player_trophy_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"trophies_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="sorted-townhall", description="List of clan members, sorted by trophies")
    async def player_th(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed = await self.player_townhall_sort(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"townhall_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="war-preferences", description="List of player's war preferences")
    async def war_opt(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        clan = await self.bot.getClan(clan)
        if clan is None or clan.member_count == 0:
            embed = disnake.Embed(description="Not a valid clan tag.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        embed = await self.opt_status(clan)
        embed.description += f"Last Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"waropt_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="war-log", description="List of clan's last 25 war win & losses")
    async def clan_war_log(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        if not clan.public_war_log:
            embed = disnake.Embed(description="Clan has a private war log.",
                                  color=disnake.Color.red())
            embed.set_thumbnail(url=clan.badge.url)
            return await ctx.edit_original_message(embed=embed)

        embed = await self.war_log(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"warlog_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="super-troops", description="List of clan member's boosted & unboosted troops")
    async def clan_super_troops(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed: disnake.Embed = await self.stroop_list(clan)
        values = embed.fields[0].value + f"\nLast Refreshed: <t:{int(time)}:R>"
        embed.set_field_at(0, name="**Not Boosting:**",value=values, inline=False)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"stroops_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)

    @clan.sub_command(name="board", description="Simple embed, with overview of a clan")
    async def clan_board(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), button_text: str = None, button_link: str = None):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
            button_text: can add an extra button to this board, this is the text for it
            button_link:can add an extra button to this board, this is the link for it
        """
        await ctx.response.defer()
        time = datetime.now().timestamp()

        embed = await self.clan_overview(ctx, clan)
        values = embed.fields[-1].value + f"\nLast Refreshed: <t:{int(time)}:R>"
        embed.set_field_at(len(embed.fields) - 1, name="**Boosted Super Troops:**", value=values, inline=False)
        buttons = disnake.ui.ActionRow()
        buttons.append_item(disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey, custom_id=f"clanboard_{clan.tag}"))
        buttons.append_item(disnake.ui.Button(label=f"Clan Link", emoji="🔗",url=clan.share_link))
        if button_text is not None and button_link is not None:
            buttons.append_item(disnake.ui.Button(label=button_text, emoji="🔗", url=button_link))

        try:
            await ctx.edit_original_message(embed=embed, components=buttons)
        except disnake.errors.HTTPException:
            embed = disnake.Embed(description="Not a valid button link.",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="compo", description="Townhall composition of a clan")
    async def clan_compo(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        """
            Parameters
            ----------
            clan: Use clan tag or select an option from the autocomplete
        """
        await ctx.response.defer()
        thcount = defaultdict(int)
        total = 0
        sumth = 0

        clan_members = []

        clan_members += [member.tag for member in clan.members]
        list_members = await self.bot.get_players(tags=clan_members, custom=False)
        for player in list_members:
            th = player.town_hall
            sumth += th
            total += 1
            thcount[th] += 1

        stats = ""
        for th_level, th_count in sorted(thcount.items(), reverse=True):
            if (th_level) <= 9:
                th_emoji = self.bot.fetch_emoji(th_level)
                stats += f"{th_emoji} `TH{th_level} ` : {th_count}\n"
            else:
                th_emoji = self.bot.fetch_emoji(th_level)
                stats += f"{th_emoji} `TH{th_level}` : {th_count}\n"

        average = round((sumth / total), 2)
        embed = disnake.Embed(title=f"{clan.name} Townhall Composition", description=stats,
                              color=disnake.Color.green())
        embed.set_thumbnail(url=clan.badge.large)
        embed.set_footer(text=f"Average Th: {average}\nTotal: {total} accounts")
        await ctx.edit_original_message(embed=embed)

    @clan.sub_command(name="capital-stats", description="Get stats on raids & donations during selected time period")
    async def clan_capital_stats(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), weekend=commands.Param(default="Current Week", choices=["Current Week", "Last Week", "Last 4 Weeks (all)"])):
        await ctx.response.defer()
        raidlog = await self.bot.coc_client.get_raidlog(clan.tag)
        choice_to_date = {"Current Week": [0], "Last Week": [1], "Last 4 Weeks (all)": [0, 1, 2, 3]}
        weekend_times = weekend_timestamps()
        weekend_dates = create_weekend_list(option=weekend)
        member_tags = [member.tag for member in clan.members]

        embeds = {}
        other_tags = []
        columns = ["Tag", "Donated", "Number of Donations", "Raided", "Number of Raids"]
        donated_data = {}
        number_donated_data = {}

        for week in weekend_dates:
            tags = await self.bot.player_stats.distinct("tag", filter={f"capital_gold.{week}.raided_clan" : clan.tag})
            other_tags += tags
        all_tags = list(set(member_tags + other_tags))
        tasks = []
        for tag in all_tags:
            results = await self.bot.player_stats.find_one({"tag": tag})
            task = asyncio.ensure_future(self.bot.coc_client.get_player(player_tag=tag, cls=MyCustomPlayer, bot=self.bot, results=results))
            tasks.append(task)
        responses = await asyncio.gather(*tasks)

        donation_text = []
        for player in responses:
            player: MyCustomPlayer
            for char in ["`", "*", "_", "~"]:
                name = player.name.replace(char, "", 10)
            sum_donated = 0
            len_donated = 0
            for week in weekend_dates:
                cc_stats = player.clan_capital_stats(week=week)
                sum_donated += sum(cc_stats.donated)
                len_donated += len(cc_stats.donated)
            donation = f"{sum_donated}".ljust(6)

            donated_data[player.tag] = sum_donated
            number_donated_data[player.tag] = len_donated

            if sum_donated == 0 and len(weekend_dates) > 1:
                continue
            if player.tag in member_tags:
                donation_text.append([f"{self.bot.emoji.capital_gold}`{donation}`: {name}", sum_donated])
            else:
                donation_text.append([f"{self.bot.emoji.deny_mark}`{donation}`: {name}", sum_donated])

        donation_text = sorted(donation_text, key=lambda l: l[1], reverse=True)
        donation_text = [line[0] for line in donation_text]
        donation_text = "\n".join(donation_text)
        donation_embed = disnake.Embed(title=f"**{clan.name} Donation Totals**", description=donation_text,color=disnake.Color.green())
        donation_embed.set_footer(text=f"Donated: {'{:,}'.format(sum(donated_data.values()))}")
        embeds["donations"] = donation_embed

        raid_weekends = []
        for week in choice_to_date[weekend]:
            raid_weekend = self.get_raid(raid_log=raidlog, before=weekend_times[week],
                                         after=weekend_times[week + 1])
            if raid_weekend is not None:
                raid_weekends.append(raid_weekend)

        if not raid_weekends:
            embed = disnake.Embed(description=f"**{clan.name} has no capital raids in the time frame - {weekend}**",
                                  color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)

        total_attacks = defaultdict(int); total_looted = defaultdict(int); attack_limit = defaultdict(int); name_list = {}
        members_not_looted = member_tags.copy()
        for raid_weekend in raid_weekends:
            for member in raid_weekend.members:
                name_list[member.tag] = member.name
                total_attacks[member.tag] += member.attack_count
                total_looted[member.tag] += member.capital_resources_looted
                attack_limit[member.tag] += (member.attack_limit + member.bonus_attack_limit)
                if len(raid_weekends) == 1 and member.tag in members_not_looted:
                    members_not_looted.remove(member.tag)

        raid_text = []
        for tag, amount in total_looted.items():
            raided_amount = f"{amount}".ljust(6)
            name = name_list[tag]
            for char in ["`", "*", "_", "~"]:
                name = name.replace(char, "", 10)
            #print(tag)
            #print(member_tags)
            if tag in member_tags:
                raid_text.append([f"\u200e{self.bot.emoji.capital_gold}`{total_attacks[tag]}/{attack_limit[tag]} {raided_amount}`: \u200e{name}", amount])
            else:
                raid_text.append([f"\u200e{self.bot.emoji.deny_mark}`{total_attacks[tag]}/{attack_limit[tag]} {raided_amount}`: \u200e{name}",amount])

        if len(raid_weekends) == 1:
            for member in members_not_looted:
                name = coc.utils.get(clan.members, tag=member)
                raid_text.append([f"{self.bot.emoji.capital_gold}`{0}/{6*len(raid_weekends)} {0}`: {name.name}",0])

        raid_text = sorted(raid_text, key=lambda l: l[1], reverse=True)
        raid_text = [line[0] for line in raid_text]
        raid_text = "\n".join(raid_text)
        raid_embed = disnake.Embed(title=f"**{clan.name} Raid Totals**", description=raid_text, color=disnake.Color.green())
        raid_embed.set_footer(text=f"Spots: {len(total_attacks.values())}/50 | Attacks: {sum(total_attacks.values())}/300 | Looted: {'{:,}'.format(sum(total_looted.values()))}")
        embeds["raids"] = raid_embed


        data = []
        index = []
        for tag in member_tags:
            name = coc.utils.get(clan.members, tag=tag)
            index.append(name.name)
            data.append([tag, donated_data[tag], number_donated_data[tag], total_looted[tag], total_attacks[tag]])

        buttons = raid_buttons(self.bot, data)
        await ctx.edit_original_message(embed=raid_embed, components=buttons)
        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)

            except:
                try:
                    await ctx.edit_original_message(components=[])
                except:
                    pass
                break
            await res.response.defer()
            if res.data.custom_id == "donations":
                await res.edit_original_message(embed=embeds["donations"])
            elif res.data.custom_id == "raids":
                await res.edit_original_message(embed=embeds["raids"])
            elif res.data.custom_id == "capseason":
                file = self.create_excel(columns=columns, index=index, data=data, weekend=weekend)
                await res.send(file=file, ephemeral=True)

    @clan.sub_command(name="capital-raids", description="See breakdown of clan's raids per clan & week")
    async def clan_capital_raids(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter), weekend=commands.Param(default="Current Week", choices=["Current Week", "Last Week", "2 Weeks Ago"])):
        await ctx.response.defer()
        raidlog = await self.bot.coc_client.get_raidlog(clan.tag)
        choice_to_date = {"Current Week" : 0, "Last Week" : 1,  "2 Weeks Ago" : 2}
        weekend_times = weekend_timestamps()

        embed = disnake.Embed(description=f"**{clan.name} Clan Capital Raids**", color=disnake.Color.green())
        raid_weekend = self.get_raid(raid_log=raidlog, before=weekend_times[choice_to_date[weekend]], after=weekend_times[choice_to_date[weekend ] + 1])
        if raid_weekend is None:
            embed = disnake.Embed(description=f"**{clan.name} has no capital raids in the time frame - {weekend}**", color=disnake.Color.red())
            return await ctx.edit_original_message(embed=embed)
        raids = raid_weekend.attack_log

        select_menu_options = [disnake.SelectOption(label="Overview", emoji=self.bot.emoji.sword_clash.partial_emoji, value="Overview")]
        embeds = {}
        total_attacks = 0; total_looted = 0
        for raid_clan in raids:
            url = raid_clan.badge.url.replace(".png", "")
            emoji = disnake.utils.get(self.bot.emojis, name=url[-15:].replace("-", ""))
            if emoji is None:
                emoji = await self.bot.create_new_badge_emoji(url=raid_clan.badge.url)
            else:
                emoji = f"<:{emoji.name}:{emoji.id}>"
            looted = sum(district.looted for district in raid_clan.districts)
            total_looted += looted
            total_attacks += raid_clan.attack_count
            embed.add_field(name=f"{emoji}\u200e{raid_clan.name}", value=f"> {self.bot.emoji.sword} Attacks: {raid_clan.attack_count}\n"
                                                                                      f"> {self.bot.emoji.capital_gold} Looted: {'{:,}'.format(looted)}", inline=False)
            select_menu_options.append(disnake.SelectOption(label=raid_clan.name, emoji=self.bot.partial_emoji_gen(emoji_string=emoji), value=raid_clan.tag))

            #create detailed embeds

            detail_embed = disnake.Embed(description=f"**Attacks on {raid_clan.name}**",color=disnake.Color.green())
            for district in raid_clan.districts:
                attack_text = ""
                for attack in district.attacks:
                    attack_text += f"> \u200e{attack.destruction}% - \u200e{attack.attacker_name}\n"
                if district.id == 70000000:
                    emoji = self.bot.fetch_emoji(name=f"Capital_Hall{district.hall_level}")
                else:
                    emoji = self.bot.fetch_emoji(name=f"District_Hall{district.hall_level}")
                if attack_text == "":
                    attack_text = "None"
                detail_embed.add_field(name=f"{emoji}{district.name}", value=attack_text, inline=False)

            embeds[raid_clan.tag] = detail_embed

        embed.set_footer(text=f"Attacks: {total_attacks}/300 | Looted: {'{:,}'.format(total_looted)}")
        embeds["Overview"] = embed
        select = disnake.ui.Select(
            options=select_menu_options,
            placeholder="Detailed View",  # the placeholder text to show when no options have been chosen
            min_values=1,  # the minimum number of options a user must select
            max_values=1,  # the maximum number of options a user can select
        )
        dropdown = [disnake.ui.ActionRow(select)]

        await ctx.edit_original_message(embed=embed, components=dropdown)

        msg = await ctx.original_message()

        def check(res: disnake.MessageInteraction):
            return res.message.id == msg.id

        while True:
            try:
                res: disnake.MessageInteraction = await self.bot.wait_for("message_interaction", check=check,
                                                                          timeout=600)
            except:
                await msg.edit(components=[])
                break

            await res.response.edit_message(embed=embeds[res.values[0]])

    @clan.sub_command(name="last-online", description="List of most recently online players in clan")
    async def last_online(self, ctx: disnake.ApplicationCommandInteraction, clan: coc.Clan = commands.Param(converter=clan_converter)):
        await ctx.response.defer()
        time = datetime.now().timestamp()
        embed = await self.create_last_online(clan)
        embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
        buttons = disnake.ui.ActionRow()
        buttons.append_item(
            disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                              custom_id=f"lo_{clan.tag}"))
        await ctx.edit_original_message(embed=embed, components=buttons)
        await ctx.edit_original_message(embed=embed)



    def get_raid(self, raid_log, after, before):
        for raid in raid_log:
            time_start = int(raid.start_time.time.timestamp())
            if before > time_start > after:
                return raid
        return None

    def create_excel(self, columns, index, data, weekend):
        df = pd.DataFrame(data, index=index, columns=columns)
        df.to_excel('ClanCapitalStats.xlsx', sheet_name=f'{weekend}')
        return disnake.File("ClanCapitalStats.xlsx", filename=f"{weekend}_clancapital.xlsx")

    @commands.Cog.listener()
    async def on_button_click(self, ctx: disnake.MessageInteraction):
        time = datetime.now().timestamp()
        if "linked_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed = await self.linked_players(ctx, clan)
            embed2 = await self.unlinked_players(ctx, clan)
            embed2.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            buttons = disnake.ui.ActionRow()
            buttons.append_item(
                disnake.ui.Button(label="", emoji=self.bot.emoji.refresh.partial_emoji, style=disnake.ButtonStyle.grey,
                                  custom_id=f"linked_{clan.tag}"))
            await ctx.edit_original_message(embeds=[embed, embed2], components=buttons)
        elif "trophies_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.player_trophy_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "waropt_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.opt_status(clan)
            embed.description += f"Last Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "warlog_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.war_log(clan)
            embed.description += f"Last Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "stroops_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.stroop_list(clan)
            values = embed.fields[0].value + f"\nLast Refreshed: <t:{int(time)}:R>"
            embed.set_field_at(0, name="**Not Boosting:**",value=values, inline=False)
            await ctx.edit_original_message(embed=embed)
        elif "clanboard_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.clan_overview(ctx, clan)
            values = embed.fields[-1].value + f"\nLast Refreshed: <t:{int(time)}:R>"
            embed.set_field_at(len(embed.fields) - 1, name="**Boosted Super Troops:**", value=values, inline=False)
            await ctx.edit_original_message(embed=embed)
        elif "townhall_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.player_townhall_sort(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)
        elif "lo_" in str(ctx.data.custom_id):
            await ctx.response.defer()
            clan = (str(ctx.data.custom_id).split("_"))[-1]
            clan = await self.bot.getClan(clan)
            embed: disnake.Embed = await self.create_last_online(clan)
            embed.description += f"\nLast Refreshed: <t:{int(time)}:R>"
            await ctx.edit_original_message(embed=embed)

    @clan_capital_raids.autocomplete("clan")
    @linked_clans.autocomplete("clan")
    @player_trophy.autocomplete("clan")
    @war_opt.autocomplete("clan")
    @clan_war_log.autocomplete("clan")
    @clan_super_troops.autocomplete("clan")
    @clan_board.autocomplete("clan")
    @getclan.autocomplete("clan")
    @clan_capital_stats.autocomplete("clan")
    @player_th.autocomplete("clan")
    @clan_compo.autocomplete("clan")
    @last_online.autocomplete("clan")
    async def autocomp_clan(self, ctx: disnake.ApplicationCommandInteraction, query: str):
            tracked = self.bot.clan_db.find({"server": ctx.guild.id})
            limit = await self.bot.clan_db.count_documents(filter={"server": ctx.guild.id})
            clan_list = []
            for tClan in await tracked.to_list(length=limit):
                name = tClan.get("name")
                tag = tClan.get("tag")
                if query.lower() in name.lower():
                        clan_list.append(f"{name} | {tag}")

            if clan_list == [] and len(query) >= 3:
                clan = await self.bot.getClan(query)
                if clan is None:
                    results = await self.bot.coc_client.search_clans(name=query, limit=5)
                    for clan in results:
                        league = str(clan.war_league).replace("League ", "")
                        clan_list.append(f"{clan.name} | {clan.member_count}/50 | LV{clan.level} | {league} | {clan.tag}")
                else:
                    clan_list.append(f"{clan.name} | {clan.tag}")
                    return clan_list
            return clan_list[0:25]