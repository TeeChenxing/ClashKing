import disnake
import coc
from main import scheduler
from CustomClasses.CustomBot import CustomClient
from utils.discord_utils import interaction_handler
from Exceptions.CustomExceptions import ExpiredComponents
from typing import List
from utils.components import clan_component
from utils.constants import TOWNHALL_LEVELS, ROLES

##REMINDER CREATION

settings_text = {
    "capital": f"**Choose settings:**\n"
               "> - Clans\n"
               "> - (optional) Attack Threshold - Ping people with this many or more attacks left\n"
               "> - (optional) Game Roles to Ping\n"
               "*Note: If you don't select optional fields, defaults will be used*",
    "clangames": f"**Choose settings:**\n"
                 "> - Clans\n"
                 "> - (optional) Game Roles to Ping | default all roles\n"
                 "> - (optional) Point Threshold - Ping people with less than this many points | default 4000\n"
                 "*Note: If you don't select the optional fields, defaults will be used*",
    "war": f"**Choose settings:**\n"
           "> - Clans\n"
           "> - (optional) Townhall Levels to Ping | default all\n"
           "> - (optional) Game Roles to Ping | default all\n"
           "> - (optional) War Types to Remind for | default all\n"
           "*Note: If you don't select the optional fields, defaults will be used*",
    "inactivity": f"**Choose settings:**\n"
                  "> - Clans\n"
                  "> - (optional) Townhall Levels to Ping | default all\n"
                  "> - (optional) Game Roles to Ping | default all\n"
                  "*Note: If you don't select the optional fields, defaults will be used*",
}

def role_options():
    options = []
    role_types = ROLES
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return role_select

def buttons(bot: CustomClient):
    page_buttons = [
        disnake.ui.Button(label="Save", emoji=bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green, custom_id="Save"),
        disnake.ui.Button(label="Custom Text", emoji="✏", style=disnake.ButtonStyle.grey, custom_id="modal_reminder_custom_text")
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)
    return buttons

def atk_threshold():
    options = []
    attack_numbers = [1, 2, 3, 4, 5]
    for number in attack_numbers:
        options.append(disnake.SelectOption(label=f"{number} attacks", value=f"{number}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Attack Threshold",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1  # the maximum number of options a user can select
    )
    return war_type_select

def townhalls(bot: CustomClient):
    options = []
    for num in reversed(TOWNHALL_LEVELS):
        options.append(disnake.SelectOption(label=f"Townhall {num}", emoji=bot.fetch_emoji(name=num).partial_emoji,
                                            value=f"th_{num}"))
    th_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Townhalls",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return th_select

def war_type():
    options = []
    war_types = ["Random", "Friendly", "CWL"]
    for war_type in war_types:
        options.append(disnake.SelectOption(label=f"{war_type}", value=f"{war_type}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select War Types",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    return war_type_select

def point_threshold():
    options = []
    attack_numbers = [250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    for number in attack_numbers:
        options.append(disnake.SelectOption(label=f"{number} points", value=f"{number}"))
    war_type_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Point Threshold",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=1  # the maximum number of options a user can select
    )
    return war_type_select


async def create_capital_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild_id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), atk_threshold(), role_options(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    attack_threshold = 1
    custom_text = ""

    embed = disnake.Embed(title="**Choose options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()


    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text)
                clan_dropdown = clan_component(bot=bot, all_clans=clans, clan_page=clan_page)
                await message.edit(embed=embed, components=[clan_dropdown, atk_threshold(), role_options(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            clan_dropdown = clan_component(bot=bot, all_clans=clans, clan_page=clan_page)
            await message.edit(embed=embed, components=[clan_dropdown, atk_threshold(), role_options(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)
            else:
                attack_threshold = res.values[0]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, atk=attack_threshold, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)


    for time in times:
        for clan in clans_chosen:
            await bot.reminders.delete_one({"$and": [
                {"clan": clan.tag},
                {"server": ctx.guild.id},
                {"type": "Clan Capital"},
                {"time": time}
            ]})
            await bot.reminders.insert_one({
                "server": ctx.guild.id,
                "type": "Clan Capital",
                "clan": clan.tag,
                "channel": channel.id,
                "time": time,
                "roles": roles_chosen,
                "attack_threshold": attack_threshold,
                "custom_text" : custom_text
            })


async def create_war_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild_id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), war_type(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    war_types = ["Random", "Friendly", "CWL"]
    custom_text = ""
    ths = list(reversed(TOWNHALL_LEVELS))

    embed = disnake.Embed(title="**Choose options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()


    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), war_type(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), war_type(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)
            elif "th_" in res.values[0]:
                ths = [int(th.split("_")[-1]) for th in res.values]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)
            elif res.values[0] in ["Random", "Friendly", "CWL"]:
                war_types = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, war_types=war_types, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)


    '''for time in times:
        for clan in clans_chosen:
            await bot.reminders.delete_one({"$and": [
                {"clan": clan.tag},
                {"server": ctx.guild.id},
                {"type": "Clan Capital"},
                {"time": time}
            ]})
            await bot.reminders.insert_one({
                "server": ctx.guild.id,
                "type": "Clan Capital",
                "clan": clan.tag,
                "channel": channel.id,
                "time": time,
                "roles": roles_chosen,
                "attack_threshold": attack_threshold,
                "custom_text" : custom_text
            })'''


async def create_games_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild_id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), point_threshold(), townhalls(bot=bot), role_options(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    points = 4000
    custom_text = ""
    ths = list(reversed(TOWNHALL_LEVELS))

    embed = disnake.Embed(title="**Choose options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()

    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), point_threshold(), townhalls(bot=bot), role_options(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), point_threshold(),
                                                        townhalls(bot=bot), role_options(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)
            elif "th_" in res.values[0]:
                ths = [int(th.split("_")[-1]) for th in res.values]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)
            else:
                points = int(res.values[0])
                embed.description = chosen_text(bot=bot, clans=clans_chosen, points=points, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)


async def create_inactivity_reminder(bot: CustomClient, ctx: disnake.ApplicationCommandInteraction, channel: disnake.TextChannel, times: List[str]):
    clans = await bot.get_clans(tags=(await bot.get_guild_clans(guild_id=ctx.guild_id)))
    clan_page = 0
    dropdown = [clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot),role_options(), buttons(bot=bot)]

    save = False

    clans_chosen = []
    roles_chosen = ROLES
    custom_text = ""
    ths = list(reversed(TOWNHALL_LEVELS))

    embed = disnake.Embed(title="**Choose options/filters**", color=disnake.Color.green())
    embed.set_footer(text="Note: If you don't select optional fields, defaults will be used")
    embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text)
    await ctx.edit_original_message(embed=embed, components=dropdown)
    message = await ctx.original_message()

    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if res.data.custom_id == "modal_reminder_custom_text":
                custom_text = await get_custom_text(bot=bot, res=res)
                embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed,
                                   components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page), townhalls(bot=bot), role_options(), buttons(bot=bot)])
            elif not clans_chosen:
                await res.send(content="Must select at least one clan", ephemeral=True)
            else:
                save = True
        elif any("clanpage_" in s for s in res.values):
            clan_page = int(next(value for value in res.values if "clanpage_" in value).split("_")[-1])
            await message.edit(embed=embed, components=[clan_component(bot=bot, all_clans=clans, clan_page=clan_page),
                                                        townhalls(bot=bot), role_options(), buttons(bot=bot)])

        elif any("clantag_" in s for s in res.values):
            clan_tags = [tag.split('_')[-1] for tag in res.values if "clantag_" in tag]
            for tag in clan_tags:
                clan = coc.utils.get(clans, tag=tag)
                if clan in clans_chosen:
                    clans_chosen.remove(clan)
                else:
                    clans_chosen.append(clan)
            embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text)
            await message.edit(embed=embed)

        elif "string_select" in str(res.data.component_type):
            if res.values[0] in ROLES:
                roles_chosen = res.values
                embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)
            elif "th_" in res.values[0]:
                ths = [int(th.split("_")[-1]) for th in res.values]
                embed.description = chosen_text(bot=bot, clans=clans_chosen, ths=ths, roles=roles_chosen, custom_text=custom_text)
                await message.edit(embed=embed)


async def get_custom_text(bot:CustomClient, res: disnake.MessageInteraction):
    await res.response.send_modal(
        title="Customize your text",
        custom_id="customtext-",
        components=[
            disnake.ui.TextInput(
                label="Extra Custom Text",
                placeholder="Extra text to send when reminder is sent (gifs, rules, etc)",
                custom_id=f"custom_text",
                required=True,
                style=disnake.TextInputStyle.paragraph,
                max_length=300,
            )
        ])
    def check(r):
        return res.author.id == r.author.id

    try:
        modal_inter: disnake.ModalInteraction = await bot.wait_for(
            "modal_submit",
            check=check,
            timeout=300,
        )
    except:
        raise ExpiredComponents
    await modal_inter.response.defer(ephemeral=True)
    await modal_inter.send(content="Custom Text Stored", delete_after=3)
    custom_text = modal_inter.text_values["custom_text"]
    return custom_text


def chosen_text(bot: CustomClient, clans: List[coc.Clan], ths=None, roles=None, atk=None, war_types=None, points=None, custom_text=""):
    text = ""
    if clans:
        text += "**CLANS:**\n"
        for clan in clans:
            text += f"• {clan.name} ({clan.tag})\n"

    if ths is not None:
        text += "\n**THS:**\n"
        if ths == list(reversed(TOWNHALL_LEVELS)):
            text += f"• All Townhall Levels\n"
        else:
            ths = [f"TH{th}" for th in ths]
            text += "• " + ", ".join(ths) + "\n"


    if war_types:
        text += "\n**WAR TYPES:**\n"
        for t in war_types:
            text += f"• {t}\n"

    if roles:
        text += "\n**ROLES:**\n"
        for role in roles:
            text += f"• {role}\n"

    if atk is not None:
        text += f"\n**Attack Threshold:** {atk}+ left\n"

    if points is not None:
        text += f"\n**Point Threshold:** ≤ {points} left\n"

    if custom_text != "":
        text += f"\n**Custom Text:** {custom_text}\n"
    return text










async def create_inactivity_reminder(bot: CustomClient, ctx: disnake.MessageInteraction, clan: coc.Clan,
                                     channel: disnake.TextChannel):
    content = f"**Choose settings ({clan.name}):**\n" \
              "> - Times to remind\n" \
              "> - (optional) Game Roles to Ping | default all roles\n" \
              "> - (optional) Point Threshold - Ping people with less than this many points | default 4000\n" \
              "*Note: If you don't select the optional fields, defaults will be used*"

    options = [  # the options in your dropdown
        disnake.SelectOption(label="24 hours of inactivity", emoji=bot.emoji.clock.partial_emoji, value="24 hr"),
        disnake.SelectOption(label="48 hours of inactivity", emoji=bot.emoji.clock.partial_emoji, value="48 hr"),
        disnake.SelectOption(label="3 days of inactivity", emoji=bot.emoji.clock.partial_emoji, value="72 hr"),
        disnake.SelectOption(label="1 week of inactivity", emoji=bot.emoji.clock.partial_emoji, value="168 hr"),
        disnake.SelectOption(label="2 weeks of inactivity", emoji=bot.emoji.clock.partial_emoji, value="336 hr"),
        disnake.SelectOption(label="Remove All", emoji=bot.emoji.no.partial_emoji, value="remove")
    ]
    time_select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=4,  # the maximum number of options a user can select
    )

    options = []
    role_types = ["Member", "Elder", "Co-Leader", "Leader"]
    for role in role_types:
        options.append(disnake.SelectOption(label=f"{role}", value=f"{role}"))
    role_select = disnake.ui.Select(
        options=options,
        placeholder="(optional) Select Roles",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )

    page_buttons = [
        disnake.ui.Button(label="Save", emoji=bot.emoji.yes.partial_emoji, style=disnake.ButtonStyle.green,
                          custom_id="Save"),
    ]
    buttons = disnake.ui.ActionRow()
    for button in page_buttons:
        buttons.append_item(button)

    dropdown = [disnake.ui.ActionRow(time_select), disnake.ui.ActionRow(role_select), buttons]

    await ctx.edit_original_message(content=content, components=dropdown)

    save = False

    times = []
    roles = role_types
    while not save:
        res: disnake.MessageInteraction = await interaction_handler(bot=bot, ctx=ctx, function=None)
        if "button" in str(res.data.component_type):
            if not times:
                await res.send(content="Must select reminder times", ephemeral=True)
            else:
                save = True
        elif "string_select" in str(res.data.component_type):
            if "hr" in res.values[0]:
                times = res.values
            elif res.values[0] in role_types:
                roles = res.values

    for time in times:
        await bot.reminders.delete_one({"$and": [
            {"clan": clan.tag},
            {"server": ctx.guild.id},
            {"type": "inactivity"},
            {"time": time}
        ]})
        await bot.reminders.insert_one({
            "server": ctx.guild.id,
            "type": "inactivity",
            "clan": clan.tag,
            "channel": channel.id,
            "time": time,
            "roles": roles,
        })

    reminders_created = ", ".join(times)
    content = f"**`{reminders_created}` Inactivity Reminders created for {clan.name}**"

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Set Custom Text", emoji="✏️", style=disnake.ButtonStyle.green,
                          custom_id="custom_text"),
        disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    await ctx.edit_original_message(content=content, components=button)

    async def get_custom_text(res: disnake.MessageInteraction):
        if res.data.custom_id == "new_reminder" or res.data.custom_id == "go_to_finish":
            await res.response.defer()
            return res.data.custom_id
        await res.response.send_modal(
            title="Customize your text",
            custom_id="customtext-",
            components=[
                disnake.ui.TextInput(
                    label="Extra Custom Text",
                    placeholder="Extra text to send when reminder is sent (gifs, rules, etc)",
                    custom_id=f"custom_text",
                    required=True,
                    style=disnake.TextInputStyle.paragraph,
                    max_length=300,
                )
            ])
        button = [disnake.ui.ActionRow(
            disnake.ui.Button(label="Create Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                              style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
            disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                              custom_id="go_to_finish"))
        ]
        await res.edit_original_message(components=button)

        def check(res):
            return ctx.author.id == res.author.id

        try:
            modal_inter: disnake.ModalInteraction = await bot.wait_for(
                "modal_submit",
                check=check,
                timeout=300,
            )
        except:
            raise ExpiredComponents
        await modal_inter.response.defer(ephemeral=True)
        await modal_inter.send(content="Custom Text Stored")
        custom_text = modal_inter.text_values["custom_text"]
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)

    if custom_text in ["new_reminder", "go_to_finish"]:
        return custom_text

    custom_text = await interaction_handler(ctx=ctx, function=get_custom_text, no_defer=True)
    await bot.reminders.update_many({
        "server": ctx.guild.id,
        "type": "inactivity",
        "clan": clan.tag,
        "channel": channel.id,
    }, {"$set": {"custom_text": custom_text}})
    return custom_text


##REMINDER DELETION

async def remove_clan_capital_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "Clan Capital"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No clan capital reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "Clan Capital",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` Clan Capital Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move


async def remove_clan_games_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "Clan Games"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No clan games reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "Clan Games",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` Clan Games Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move


async def remove_war_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "War"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No war reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "War",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` War Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move


async def remove_inactivity_reminder(bot, ctx: disnake.MessageInteraction, clan: coc.Clan):
    clan_capital_reminders = bot.reminders.find(
        {"$and": [{"clan": clan.tag}, {"type": "inactivity"}, {"server": ctx.guild.id}]})

    reminders = []
    for reminder in await clan_capital_reminders.to_list(length=100):
        reminders.append([reminder, float(str(reminder.get('time')).replace("hr", ""))])

    reminders = sorted(reminders, key=lambda l: l[1], reverse=False)

    options = []
    for reminder in reminders:
        reminder = reminder[0]
        options.append(
            disnake.SelectOption(label=f"{reminder.get('time')} reminder", emoji=bot.emoji.clock.partial_emoji,
                                 value=f"{reminder.get('time')}"))

    button = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Remove Another Reminder", emoji=bot.emoji.right_green_arrow.partial_emoji,
                          style=disnake.ButtonStyle.grey, custom_id="new_reminder"),
        disnake.ui.Button(label="I am done!", emoji=bot.emoji.no.partial_emoji, style=disnake.ButtonStyle.red,
                          custom_id="go_to_finish"))
    ]

    if not options:
        content = f"**No inactivity reminders set up for {clan.name}**"
        await ctx.edit_original_message(content=content, components=button)
        res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
        next_move = res.data.custom_id
        return next_move

    content = "**Choose reminder times to remove from list**"
    select = disnake.ui.Select(
        options=options,
        placeholder="Select Reminder Times",  # the placeholder text to show when no options have been chosen
        min_values=1,  # the minimum number of options a user must select
        max_values=len(options),  # the maximum number of options a user can select
    )
    dropdown = [disnake.ui.ActionRow(select)]
    await ctx.edit_original_message(content=content, components=dropdown)

    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    for value in res.values:
        await bot.reminders.delete_one({
            "server": ctx.guild.id,
            "type": "inactivity",
            "clan": clan.tag,
            "time": value
        })

    reminders_removed = ", ".join(res.values)
    content = f"**`{reminders_removed}` Inactivity Reminders removed for {ctx.guild.name}**"
    await ctx.edit_original_message(content=content, components=button)
    res: disnake.MessageInteraction = await interaction_handler(ctx=ctx)
    next_move = res.data.custom_id
    return next_move