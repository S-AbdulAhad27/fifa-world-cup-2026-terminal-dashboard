from tabulate import tabulate
import os
import subprocess
import re

from api import get_server_data, load_file_data, matches_url, standing_url, player_url
from logging_config import logger

from collections.abc import Generator, Iterable, Iterator
from typing import Any, Literal
import time





def main():
    START_SCREEN = """
==================================================
 ⚽  WELCOME TO THE FIFA WORLD CUP 2026 DASHBOARD ⚽
==================================================
    1. View Live Match Screen (In-Play)
    2. View Group Standings (Points Table)
    3. View Knockout Stage Screen (Tournament Bracket)
    4. View Tournament Leaders (Top Stats)
    5. Exit Program """

    while True:
        try:
            subprocess.run("cls" if os.name == 'nt' else 'clear', shell=True) # Clear the terminal for clean display.
            print(START_SCREEN)

            build_terminal_dashboard(
                input("👉 Enter your choice (1-5): ").strip()
            )
            input("\nPress Enter to return to main menu.. ")

        except ValueError:
            time.sleep(1.5)
            continue
        except EOFError:
            break



# Get team name with special id.
def get_team_name(team_id: str, api_data: dict=load_file_data(standing_url))-> str:
    """
    Find team name in Api response with the help of team id.

    Read json file for the Api response team data which  save in the file.

    :param team_id: specific team id of that team which name you want to find.
    :param api_data: all the api reponse data, defualt to save data.
    :type team_id: str
    :type api_data: dict.
    :raises TypeError: if api data is not dict or api_date Resullts is not iterable.
    :raises IndexError: If the Name is emty list.
    :raises AttributeError: if the team or Name do not provide the expecte dict.
    :return: if  the Team is Exist in api_data it will give A exact Team Name else say Team not found.
    :rtype: str
    """

    try:
        for item in api_data["Results"]:
            if not team_id:
                raise TypeError
                break
            if "Team" in item and item["Team"].get("IdTeam") == team_id:
                return item["Team"].get("Name")[0].get("Description")
        return "Team not found"

    except (KeyError, TypeError, IndexError) as e:
        logger.error(e)
        return "Team not found"


# Get group name with special id.
def get_group_name(group_id: str, all_api_data: dict=load_file_data(standing_url))-> str:
    """
    Search a group name in all api response by group id.

    Read json file for the Api response which  save in the file.

    :param group_id: The unique ID of the Group for search for in the Api reponse.
    :param all_api_data:The complete Api response containing group information, defualt to save data.

    :type group_id: str
    :type all_api_data: dict

    :return: The matching group name, Return Error fallback description if the api data parsed invalid key or missing key.
    :rtype: str
    """
    try:
        if not isinstance(group_id, str) or not group_id:
            raise TypeError

        group_name: str= next(
        (
            d["Group"][0]["Description"]
            for d in all_api_data.get("Results", [])
            if "Group" in d
            and "IdGroup" in d
            and isinstance(d["Group"], list)
            and d["Group"]
            and "Description" in d["Group"][0]
            and d["IdGroup"] == group_id
        ),
           (g["Group"][0]["Description"] for g in all_api_data.get("Results", "") if group_id == g["IdGroup"])
        )

    except (KeyError, TypeError, IndexError) as e:
        logger.error(f"An error occurred while parsing API data: {e}")
        group_name = "Error Fallback Description"

    return group_name



#1. Live Match Screen (Ongoing Games)
def get_live_scores(raw_data: dict) -> str:
    if not raw_data:
        header = ['FIFA WORLD CUP LIVE']
        message = [['Status: No live mactches are currently in progress\nPlease check back later during match hours']]

        raw_data = tabulate(message, headers=header, tablefmt="rounded_grid", colalign=('center', ) * 1)

    else:
        raw_data = tabulate(raw_data, headers='keys', tablefmt='simple_grid', colglobalalign='center')

    return raw_data


def parse_match_events(
        match_id: str | None=None,
        raw_data: dict= {}
    ) -> dict[Any, Iterable[str]]:
    ...


#2. Group Standings Screen (Points Table)
def calculate_standings(all_data: dict) -> list[dict]:
    """
    Search and calculate all the fields which is important in Group Standings screen from Api fatch data.

    :param all_data: all the api response data.
    :type all_data: dict.
    :raises KeyError: if the expected Results, Position, IdGroup, IdTeam, Won, Draw etc are missing or contain in the api response.
    :raises TypeError: if the won, againsts, draw key values are an int in the api response data or If numeric fields contain values that cannot be
    used in arithmetic operations.
    :return: filtered list of dictionarys containing important fields of groups standings eg position, team name, won, draw etc.
    :rtype: list[dict].
    """
    groups_data = []

    for d in all_data['Results']:
        groups_data.append({

                get_group_name(d["IdGroup"]) :[
                {
                    "Position": d["Position"],
                    "Team" : get_team_name(d["Team"].get("IdTeam"), all_data),
                    "Won" : d["Won"],
                    "Draws" : d["Drawn"],
                    "Lost" : d["Lost"],
                    "GD" : GD if (GD := f"{d['For'] - d['Against']:+d}") == f"{d['GoalsDiference']:+d}" else f"{d['GoalsDiference']:+d}",
                    "Points" : pts if (pts := (d["Won"] * 3) + (d["Drawn"] * 1)) == d["Points"] else d.get("Points", "")
                }
            ]
        })

    return  groups_data



def filter_teams_by_rank(groups_dict: list) -> dict[list]:
    """
    keep all same group sorted like Group (A, B , C) together and sort teams by their rank or position in all the groups.

    :param groups_dict: contained dict of all groups in the list.
    :type group_dict: list of dicts.
    :raises KeyError: if expected keys are not in a group or keys are missing.
    :raises IndexError: if expected lists are empty in any group.
    :raises TypeError: if group_dict is not list or trying to sort None.
    :return: A filtered and clean dict of group standings data with sorted by position.
    :rtype: dict

    """

    new_group = {}
    current_group = ""
    try:

        for group in sorted(groups_dict, key=lambda g: (list(g.keys())[0], list(g.values())[0][0]["Position"])):
            for d in group:
                if d != current_group:
                    current_group = d
                    new_group[current_group] = group[d]

                elif d == current_group:
                    new_group[current_group].append(group[current_group][0])

        return new_group

    except (KeyError, IndexError) as e:
        logger.error(e)
        raise



#3. Knockout Stage Screen (Round of 16 to Final)
def filter_knockout_matches(raw_data: dict)-> tuple[list[dict], list[dict]]:
    """
    complete knockout matches data with Date, Stage, TeamName, Score and more of completed matches and scheduled.

    :param raw_data: Api respose containing all knockouts matches with completed matches and scheduled matches all together.
    :type raw_data: dict
    :raises KeyError: if expected keys are missing from the Api response.
    :raises TypeError: if data is not dict, data is None or Any data fields are None.
    :raises IndexError: if expected lists (such as StageName, TeamName, or Stadium Name) are empty.
    :rerurn: A tuple containing lists of completed matches scheduled marches.
    :rtype: tuple of (list of dict, list of dict)
    """
    completed_matches = []
    scheduled_matches = []

    for match in raw_data["Results"]:
        try:
            match_id = match["IdMatch"]
            match_num = match["MatchNumber"]
            date = match["Date"]
            stage = match["StageName"][0]["Description"]
            home_team = match["Home"]["TeamName"][0]["Description"] if match["Home"] is not None else match["PlaceHolderA"]
            home_team_score = home_team_score if (home_team_score := match["HomeTeamScore"]) is not None else ""
            away_team = match["Away"]["TeamName"][0]["Description"] if match["Away"] is not None else match["PlaceHolderB"]
            away_team_score = match["AwayTeamScore"] if match["AwayTeamScore"] is not None else ""
            winner = match["Winner"]
            stadium = match["Stadium"]["Name"][0]["Description"]


            if winner is not None and home_team_score != "" and away_team_score != "":
                completed_matches.append(
                    {
                        "Match_No" : match_num,
                        "Date" : re.search(r"^([\d-]+)", date).group(1),
                        "Stage" : stage,
                        "Home Team" : home_team,
                        "Score" : f"{home_team_score}-{away_team_score}",
                        "Away Team" : away_team,
                        "Winner" : get_team_name(winner),
                        "Stadium" : stadium,
                    }
                )
            elif winner is None and home_team_score == "" and away_team_score == "":
                scheduled_matches.append(
                    {
                        "Match_No" : match_num,
                        "Date" : re.search(r"^([\d-]+)", date).group(1),
                        "Stage" : stage,
                        "Home Team" : home_team,
                        "Score" : f"{home_team_score} vs {away_team_score}",
                        "Away Team" : home_team,
                        "Stadium" : stadium,
                    }
                )

        except (KeyError, TypeError, ValueError) as e:
            print(f"Data Error: Missing key {e} in Match Number {match.get('MatchNumber', 'Unknown')}")
            raise

    return completed_matches, scheduled_matches


def format_knockout_bracket(knockout_matches : tuple)-> tuple[str, str, str]:

    completed_matches, scheduled_matches = knockout_matches

    try:
        for match in completed_matches[:]:
            if match["Stage"] == "First Stage":
                completed_matches.remove(match)
            else:
                del match["Stadium"]

        all_knockout_matches = completed_matches, scheduled_matches

        return all_knockout_matches

    except (KeyError, TypeError) as e:
        logger.error(e)
        raise


def display_stage_results(all_knockout_matches : list ) -> Iterator[tuple[str, str, list[str]]]:
    """
    Take the all knockout matches data as of single list [completed matches] or [scheduled matches]
    and yield a tuple containing (header text of match stats, formatted table
    of round stats, and the list of all round names).

    :param all_knockout_matches: a list contain dict of all knockout round match.
    :type all_knockout_matches: list[dict]
    :raises TypeError:
    :raises KeyError:
    :return: yield a tuple of (header text of match stats, formatted table
     of round stats, and the list of all round names).

    :rtype: Iterator[tuple[str, str, list[str]]].








    """
    round_order = ["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Bronze final", "Final"]
    try:
        for stage in round_order:
            current_matches = [
                match for match in all_knockout_matches if match["Stage"] == stage
            ]
            if not current_matches:
                break

            yield (
                f"\n{'='*20} {stage.upper()} {'='*20}",
                tabulate(current_matches, headers="keys", tablefmt="simple_grid", colalign=("center",) * 7),
                round_order
            )
    except(TypeError, KeyError) as e:
        logger.error(e)
        raise



#4. Tournament Leaders (Top Stats)
def get_top_scorers(raw_data: tuple, limit: int=5)-> tuple[list[dict], list[dict]]:
    """
     Show limited top Players Statistic data of Attackers and Goalkeepers like their Name, Country, minutes played and more.

     :param raw_data: Statistic Data of all players.
     :type raw_date: tuple of lists.
     :param limit: Maximum Number of Players to return, defualts to 5.
     :type limit: int
     :raises ValueError: if raw_data is not a tuple of list or contains invalid lists.
     :raises TypeError: if raw_date is None.
     :return: A tuple containing lists of top attackers and top goalkeepers.
     :rtype: tuple of (list of dict, list of dict).

    """
    try:
        attackers_data, goalkeepers_data = raw_data

        sorted_top_attackers = sorted(attackers_data, key= lambda players: (players["goals"], players["assists"], -players["minutes"]), reverse=True)
        sorted_top_goalkeepers = sorted(goalkeepers_data, key= lambda goalkeeper: (goalkeeper["gk_clean_sheets"], goalkeeper["gk_minutes"]), reverse=True)

        top_scorer_attackers = sorted_top_attackers[:limit]
        top_scorer_goalkeepers = sorted_top_goalkeepers[:limit]

        return top_scorer_attackers, top_scorer_goalkeepers

    except (ValueError, KeyError, TypeError) as e:
        logger.error(e)
        raise


def process_player_stats(raw_data: dict)-> tuple[list[dict], list[dict]]:
    """
    Separate attackers and goalkeepers from the API response, convert the required statistics to float values, and remove unnecessary fields for each player type.

    :param raw_data: Api response data contained all the players statistic.
    :type raw_data: dict
    :raises: None. KeyError and ValueError are handled internally.
    :return: Processed attacker and goalkeeper statistics.
    :rtype: tuple[list[dict], list[dict]].
    """
    goalkeepers_data = []
    attackers_data = []

    try:
        for player_data in raw_data.get("Results", []):

            if player_data["gk_games"] and player_data["gk_minutes"]:

                if player_data["gk_clean_sheets"] and player_data["gk_games"] and player_data["gk_minutes"]:
                    player_data["gk_games"] = float(player_data["gk_games"])
                    player_data["gk_minutes"] = float(player_data["gk_minutes"])
                    player_data["gk_clean_sheets"] = float(player_data["gk_clean_sheets"])

                    del player_data["minutes"], player_data["goals"], player_data["assists"]
                    goalkeepers_data.append(player_data)

            else:
               if player_data["minutes"] and player_data["goals"] and player_data["assists"]:
                    player_data["minutes"] = float(player_data["minutes"])
                    player_data["goals"] = float(player_data["goals"])
                    player_data["assists"] = float(player_data["assists"])

                    del player_data["gk_games"], player_data["gk_minutes"], player_data["gk_clean_sheets"]
                    attackers_data.append(player_data)

        return attackers_data, goalkeepers_data

    except (KeyError, ValueError) as e:
            logger.error(f"{e} Something went wronge try again")
            raise



#5. Utility / Dashboard Display Functions
def build_terminal_dashboard(screen_type: Literal['1', '2', '3', '4', '5']) -> None:
    """
    Take user input screen choice and Display fifa world processed data in table format on the screen.

    :param screen_type: Must be exactly '1', '2', '3','4', or '5' as a string.
    :param processed_data:
    :type screen_type: LitralStr['1' '2' '3' '4', '5'].

    :raises ValueError: if screen_type doesn't literal '1','2', '3', '4' as string or input incorrect type.
    :raises EOFError: if user input screen_type is exactly '5' as string.

    """

    if screen_type not in ['1', '2', '3', '4', '5']:
        print("\nPlease type correct number..")
        raise ValueError


    if screen_type == "1":
        print(get_live_scores(parse_match_events()))


    elif screen_type == "2":
        group = filter_teams_by_rank(calculate_standings(get_server_data(standing_url)))
        print(*[
                f"\t{group_name.center(40, '-')}\n {tabulate(group[group_name], headers='keys', tablefmt='grid', colglobalalign='center')}\n"
                for group_name in group
            ], sep='\n')


    elif screen_type == "3":

        completed_matches, scheduled_matches = format_knockout_bracket(filter_knockout_matches(get_server_data(matches_url)))
        round_indx = 0

        if completed_matches:
            print('''
    ╭────────────────────────────────────────────────────╮
    │                Completed Matches                   │
    ╰────────────────────────────────────────────────────╯'''
            )
            for header, table_data, round_order in display_stage_results(completed_matches):
                try:
                    print(header)
                    print(table_data)

                    if round_indx < 5:
                        round_indx += 1

                    choice = input(f"\n👉 Press Enter to see {round_order[round_indx]} results | Type n/No to exit... ").lower()
                    if (choice == "n" or choice == "no"):
                        print(f"\t\n ==== You have Exit the Knockout Stage Screen at {round_order[round_indx-1]} ====")
                        break
                except StopIteration:
                    print('exit')
                    break

        if scheduled_matches:
            for data in display_stage_results(scheduled_matches):
                print(data)
        else:
            print('''
    ╭─────────────────────────────────────────────────────────╮
    │ Status: No Scheduled mactches are currently in progress │
    ╰─────────────────────────────────────────────────────────╯'''
            )


    elif screen_type == "4":
        attackers, goalkeepers = get_top_scorers(process_player_stats(get_server_data(player_url)))
        if attackers:
            print("\t ====== Attackers Top Scores =====")
            print(tabulate(attackers, headers="keys", tablefmt="simple_grid",showindex=range(1, 6), colglobalalign="center"),"\n")

        if goalkeepers:
            print("\t ===== Goalkeepers Top Scores ======\n")
            print(tabulate(goalkeepers, headers="keys", tablefmt="simple_grid", colglobalalign="center"))


    elif screen_type == "5":
        print("""
    ==================================================
         👋 Exiting FIFA World Cup Dashboard...
        Thank you for using the application! Goodbye! ⚽
    =================================================="""
        )
        raise EOFError





if __name__ == '__main__':
    main()
