import requests
import json
from requests.exceptions import ConnectionError, HTTPError, Timeout, MissingSchema, InvalidSchema 
import csv
from logging_config import logger
from typing import Any



standing_url = "https://api.fifa.com/api/v3/calendar/17/285023/289273/standing?language=en&count=200"

matches_url = "https://api.fifa.com/api/v3/calendar/matches?language=en&count=500&idSeason=285023"

stages_url = "https://api.fifa.com/api/v3/stages?idSeason=285023&language=en"

player_url = 'players-selected-columns.csv'


def main():
    print(get_server_data(input('1. Standing_data\n2. Mactches_data\n3. Stages_data\n4. Players_data\nType : ')))



def get_server_data(data_url: str) -> dict[str, list[dict[str, Any]]]:
    """
    Fetch fifa world cup data from the server, based on the Api data Url and handles all network/HTTP
    errors internally.

    :param data_url: Specific Api data url include matches_url, standing_url, stage_url, player_url.
    :type data_url: LiteralString[matches_url, standing_url, stages_url, player_url].

    :return: Dictionary containing json parsed Api data or return load file saved data if any error 
    occured. 
    :rtype: dict[str, list[dict[str, Any]]]
 
    """
    try:
        headers:dict[str, str]= {
            "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
        }

        response = requests.get(data_url, headers=headers, timeout=5)
        response.raise_for_status()
        
        data:Any = response.json()

        if data:
            save_server_data(data)
            return data
        
        return load_file_data(data_url)
    
    except (ConnectionError, Timeout, HTTPError, MissingSchema, InvalidSchema) as e:
        logger.error("Latest data is currently unavailable, Displaying data from July 19, 2026 instead.")
        
        return load_file_data(data_url)



def load_file_data(api_data_url : str) -> dict[str, Any]:
    """
    Load fifa world cup data from the apropriate local file based on the Api data Url.

    :param api_data_url: Api data url.
    :type api_data_url: str.

    :raises JSONDecodeError: if the file is emty of ccompletely invalid.
    :raises FileNotFoundError: if File or directory doesn't exists at the specified path
    or any typos in the filename. 

    :return: Dictionary containing Api save data based on the Api data url.
    :rtype: dict[list[str, Any]]

    """
    filename = ''
    try:
        if "standing" in api_data_url:
            filename = "standings_data.json"
            
        elif "matches" in api_data_url:
            filename = "matches_data.json"

        elif "players" in api_data_url and ".csv" in api_data_url:
            filename = converted_csv_to_json("players-selected-columns.csv")

        with open(filename, "r") as f:
            data = json.load(f)

        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(e)
        


def save_server_data(api_data: dict) -> None:
    """
    Get a dict containing api data and save in the json file with related file name.

    :param api_data: A dictionary containing Api data.
    :type api_data: dict[list[str]]
    :raises PermissionError: if access is restricted.
    :raises TypeError: argument of type 'NoneType' is not iterable.
    :return: None.

    """
    try:
        for d in api_data.get("Results", []):
            if "StageName" in d or ("IdGroup" in d and d["IdGroup"] is None):
                filename: str= "matches_data.json"
                break

            elif ("Stadium" in d["Team"] and d["Team"]["Stadium"] is None) or ("IdGroup" in d and d["IdGroup"] is not None):
                filename: str = "standings_data.json"
                break

        with open(filename, "w") as f:
            json.dump(api_data, f)

    except (KeyError, FileNotFoundError, UnboundLocalError, PermissionError, TypeError) as e:
        logger.error(e)



def converted_csv_to_json(file_url_path: str) -> str:
    """
    Convert csv into json file and return the filename in json format.

    :param file_url_path: Csv file containing player data.
    :type file_url_path: str.

    :raises ValueError: if the file_url_path isn't string.
    :raises TypeError: If you pass Empty file or invalid data type.
    :raises PermissionError: if file access is restrited.

    :return: Name of player data json file as str.
    :rtype: str.
    """

    player_stats_data: dict[str, list[dict[str,str]]] = {"Results": []}
    json_filename = "players_stats.json"

    try:
        with open(file_url_path, newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                player_stats_data["Results"].append(row)
                

        with open(json_filename, 'w') as f:
            json.dump(player_stats_data, f)
    
        return json_filename
    
    except (ValueError, TypeError, PermissionError) as e:
        logger.error(f"Player data is not available now or having troulble to load this data | Error : {e}")



   

if __name__ == "__main__":
    main()