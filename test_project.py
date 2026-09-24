import pytest
from unittest.mock import patch, mock_open, DEFAULT, ANY
from requests.exceptions import HTTPError, ConnectionError
import logging

from api import get_server_data, stages_url, standing_url, player_url, matches_url
from api import load_file_data, save_server_data, converted_csv_to_json

from project import get_team_name, get_group_name, calculate_standings, filter_teams_by_rank
from project import filter_knockout_matches, format_knockout_bracket, display_stage_results
from project import get_top_scorers, process_player_stats
from project import build_terminal_dashboard


SAMPLE_STANDING_DATA = {
    "Results" : [
        {
            "IdGroup": "289284",
            "Position": 1,
            "Team": {"IdTeam": "43922", "Name": [{"Locale": "en-GB", "Description": "Argentina"}]},
            "Won": 3,
            "Drawn": 0,
            "Lost": 0,
            "For": 8,
            "Against": 1,
            "GoalsDiference": 7,
            "Points": 9,
        }
    ]
}


@pytest.fixture
def fifa_worldcup_save():
    global SAMPLE_STANDING_DATA

    def custom_load_file_data(url):
        if url == standing_url:
            return SAMPLE_STANDING_DATA
        elif url == matches_url:
            return {'Results' : [load_file_data(matches_url)["Results"][0]]}
        elif url == player_url:
            return {'Results' : [
                load_file_data(player_url)['Results'][1],
                load_file_data(player_url)['Results'][41],
                load_file_data(player_url)['Results'][179],
                load_file_data(player_url)['Results'][11],
                load_file_data(player_url)['Results'][17],
                load_file_data(player_url)['Results'][235]
            ]}
        else:
            return {}

    with patch("api.load_file_data", side_effect = custom_load_file_data):

        yield {
            "matches_data" : custom_load_file_data(matches_url),
            "standing_data" : custom_load_file_data(standing_url),
            "player_data" : custom_load_file_data(player_url)
        }


#   ==================================== test_api.py ========================================


@pytest.mark.parametrize("url", [standing_url, matches_url, stages_url])
def test_get_server_data_success(url):

    with patch.multiple('api', requests=DEFAULT, save_server_data=DEFAULT) as mock_data:
        mock_data['requests'].get.return_value.json.return_value = {"ContinuationHash": None, "Results": [{"IdStage": "289273", "IdGroup": "289275"}]}

        result = get_server_data(url)

    assert result == {"ContinuationHash": None, "Results": [{"IdStage": "289273", "IdGroup": "289275"}]}

    mock_data['save_server_data'].assert_called_once_with({"ContinuationHash": None, "Results": [{"IdStage": "289273", "IdGroup": "289275"}]})
    mock_data['requests'].get.assert_called_once_with(url, headers=ANY, timeout=ANY)



@patch.multiple('api', requests=DEFAULT, load_file_data=DEFAULT)
@pytest.mark.parametrize(
    "url", [standing_url, matches_url, stages_url]
)
def test_get_server_data_error_raises(url, caplog, **kwargs):

    mock_get = kwargs['requests']
    mock_load_file_data = kwargs['load_file_data']

    mock_get.get.side_effect = [HTTPError('Error'), ConnectionError()]
    mock_load_file_data.return_value = {"ContinuationHash": None, "Results": [{"IdStage": "289273", "IdGroup": "289275"}]}

    result = get_server_data(url)

    assert result == {"ContinuationHash": None, "Results": [{"IdStage": "289273", "IdGroup": "289275"}]}

    mock_load_file_data.assert_called_once_with(url)
    assert 'Latest data is currently unavailable' in caplog.text
    assert "Displaying data from July 19, 2026 instead." in caplog.text



@pytest.mark.parametrize(
    "url", [standing_url, matches_url]
)
@patch('builtins.open', new_callable=mock_open, read_data='{"ContinuationHash": null, "Results": [{"IdStage": "289273", "IdGroup": "289275"}]}')
def test_load_file_data(mock_load_file, url):

    result = load_file_data(url)

    mock_load_file.assert_called_once_with(ANY, 'r')
    assert result == {"ContinuationHash": None, "Results": [{"IdStage": "289273", "IdGroup": "289275"}]}



@patch('builtins.open', new_callable=mock_open)
def test_save_server_data(mock_save):

    save_server_data({"ContinuationHash": None, "Results": [{"IdStage": "289273", "IdGroup": None }]})

    mock_save.assert_called_once_with(ANY, 'w')
    mock_save().write.assert_called()


@patch('builtins.open', new_callable=mock_open,
read_data="""player,team_country,minutes,goals,assists,gk_games,gk_minutes,gk_clean_sheets
Achref Abada,Algeria,,,,,,
Adil Boulbina,Algeria,19.0,0.0,0.0,,,
Amine Gouiri,Algeria,251.0,1.0,0.0,,,"""
)
def test_converted_csv_to_json_success(mock_file):

    result = converted_csv_to_json("players-selected-columns.csv")

    assert result == 'players_stats.json'
    assert mock_file.call_count == 2
    mock_file.assert_called_with("players_stats.json", 'w')



#      ================================ test_project ================================


def test_get_team_name_valid_case():

    assert get_team_name("43942") == "England"
    assert get_team_name("44005") == "Uzbekistan"
    assert get_team_name("43995") == "Czechia"



def test_get_team_name_invalid_case():

    assert get_team_name(43942) == "Team not found"
    assert get_team_name("") == "Team not found"
    assert get_team_name({'team_id' : '44005'}) == "Team not found"


def test_get_group_name_with_valid_id():

    assert get_group_name("289286") == "Group L"
    assert get_group_name("289283") == "Group I"
    assert get_group_name("289285") == "Group K"


def test_get_group_name_with_invalid_id():

    assert get_group_name(289283) == "Error Fallback Description"
    assert get_group_name({"IdGroup" : "289283"}) == "Error Fallback Description"
    assert get_group_name("") == "Error Fallback Description"



def test_calculate_standings(fifa_worldcup_save):
    groups = calculate_standings(fifa_worldcup_save['standing_data'])

    assert list(groups[0].keys())[0] == "Group J"
    assert isinstance(groups[0]['Group J'], list)

    assert groups[0]['Group J'][0]['Position'] == 1 and groups[0]['Group J'][0]['Team'] == "Argentina"
    assert groups[0]['Group J'][0]['Won'] == 3 and groups[0]['Group J'][0]['Draws'] == 0 and groups[0]['Group J'][0]['Lost'] == 0
    assert groups[0]['Group J'][0]['GD'] == '+7' and groups[0]['Group J'][0]['Points'] == 9


def test_calculate_standings_error_raises():
    incorrect_standing_data = {
        "Data" : [
            {
                "IdGroup": "289284",
                "Position": 1,
                "Team": {"IdTeam": "43922", "Name": [{"Locale": "en-GB", "Description": "Argentina"}]},
                "Won": 3,
                "Drawn": 0,
                "Lost": 0,
                "For": 8,
                "Against": 1,
                "GoalsDiference": 7,
                "Points": 9,
            }
        ]
    }

    with pytest.raises(KeyError):
        calculate_standings(incorrect_standing_data)



def test_filter_teams_by_rank_success():

    all_fifa_groups_name = [
        "Group A", "Group B", "Group C", "Group D",
        "Group E", "Group F", "Group G", "Group H",
        "Group I", "Group J", "Group K", "Group L"
    ]

    groups = filter_teams_by_rank(calculate_standings(load_file_data(standing_url)))

    assert len(groups) == len(all_fifa_groups_name)
    assert list(groups.keys()) == all_fifa_groups_name
    assert len(groups['Group A']) == 4

    assert groups['Group A'][0]['Position'] == 1 and groups['Group A'][1]['Position'] == 2 \
        and groups['Group A'][2]['Position'] == 3 and groups['Group A'][3]['Position'] == 4
    assert isinstance(groups['Group L'][1]['GD'], str) and '+' in groups['Group L'][1]['GD']


def test_filter_teams_by_rank_success_failure(caplog):

    incorrect_standing_data = [
        {key: [{k: v for k, v in item.items() if k != 'Position'} for item in value]
        for key, value in group.items()}
        for group in calculate_standings(load_file_data(standing_url))
    ]

    with caplog.at_level(logging.INFO):
        with pytest.raises((KeyError, TypeError, AttributeError)):
            filter_teams_by_rank(incorrect_standing_data)


    assert ('Position' in record for record in caplog.record_tuples)



def test_filter_knockout_matches_success(fifa_worldcup_save):

    # test this with half data of one dict
    half_matches_data = fifa_worldcup_save['matches_data']

    results = filter_knockout_matches(half_matches_data)

    assert isinstance(results, tuple) and len(results) == 2
    assert isinstance(results[0], list) and isinstance(results[0][0], dict)

    assert results[0][0]['Match_No'] == 1 and results[0][0]['Date'] == '2026-06-11' and results[0][0]['Stage'] == 'First Stage' \
        and results[0][0]['Home Team'] == 'Mexico' and results[0][0]['Score'] == '2-0' and results[0][0]['Away Team'] == 'South Africa' \
        and results[0][0]['Winner'] == 'Mexico' and results[0][0]['Stadium'] == 'Mexico City Stadium'


def test_filter_knockout_matches_failure(fifa_worldcup_save):

    # matches data without 'Results' key
    incorrect_matches_data = {key: value for key, value in fifa_worldcup_save['matches_data'].items() if key != 'Results'}
    incorrect_matches_data_list = [{key : value} for key, value in fifa_worldcup_save['matches_data'].items()]

    with pytest.raises(KeyError):
        filter_knockout_matches(incorrect_matches_data)
    with pytest.raises(TypeError):
        filter_knockout_matches(incorrect_matches_data_list)


def test_format_knockout_bracket_success(fifa_worldcup_save):
    sample_matches_data = fifa_worldcup_save['matches_data']
                                            # test with unnecessary key 'Stadium' and removing First Stage of dict.
    knockout_data_result1 = format_knockout_bracket(filter_knockout_matches(sample_matches_data))
    data_result2 = format_knockout_bracket(filter_knockout_matches({'Results' : [load_file_data(matches_url)["Results"][73]]}))

    assert isinstance(knockout_data_result1, tuple) and len(knockout_data_result1) == 2
    assert isinstance(knockout_data_result1[0], list) and len(knockout_data_result1[0]) == 0

    assert list(data_result2[0][0].keys()) == ['Match_No', 'Date', 'Stage', 'Home Team', 'Score', 'Away Team', 'Winner']



def test_format_knockout_bracket_failured(caplog):

    incorrect_knockout_data = ([{'Match_No': 76, 'Date': '2026-06-29', 'Home Team': 'Brazil', 'Score': '2-1', 'Away Team': 'Japan',}], [{}])
    incorrect_knockout_data_dict = None

    with caplog.at_level(logging.ERROR):
        with pytest.raises(KeyError):
            #  does not contain any important key 'Stage' data
            format_knockout_bracket(incorrect_knockout_data)
        with pytest.raises(TypeError):
            format_knockout_bracket(incorrect_knockout_data_dict)

    assert any(log_tuple[1] == 40 or log_tuple[2] == 'ERROR' for log_tuple in caplog.record_tuples)


def test_display_stage_results_valid():
    mock_matches = [
        {'Match_No': 73, 'Stage': 'Round of 32', 'Home Team': 'South Africa', 'Score': '0-1', 'Away Team': 'Canada'},
        {'Match_No': 90, 'Stage': 'Round of 16', 'Home Team': 'Canada', 'Score': '0-3', 'Away Team': 'Morocco'}
    ]

    gen = display_stage_results(mock_matches)

    gen_result_one = next(gen)

    assert isinstance(gen_result_one, tuple) and len(gen_result_one) == 3
    assert '== ROUND OF 32 ==' in gen_result_one[0]
    assert  'South Africa' in gen_result_one[1] and 'Canada' in gen_result_one[1] and 'Match_No' in gen_result_one[1]
    assert "Quarter-final" in gen_result_one[2] and "Semi-final" in gen_result_one[2] and "Bronze final" in gen_result_one[2]

    gen_result_two = next(gen)

    assert isinstance(gen_result_two, tuple) and len(gen_result_two) == 3
    assert '== ROUND OF 16 ==' in gen_result_two[0]
    assert  'Morocco' in gen_result_two[1] and 'Canada' in gen_result_two[1] and 'Match_No' in gen_result_two[1]
    assert "Quarter-final" in gen_result_two[2] and "Semi-final" in gen_result_two[2] and "Bronze final" in gen_result_two[2]

    with pytest.raises(StopIteration):
        next(gen)


def test_display_stage_results_failure():
    # Match data without unpacked tuple.
    mock_match_tuple = (
        [{'Match_No': 73, 'Stage': 'Round of 32', 'Home Team': 'South Africa', 'Score': '0-1', 'Away Team': 'Canada'}],
        []
    )
    # Test without important 'Stage' key.
    mock_match_invalid_dict = [
        {'Match_No': 73, 'Home Team': 'South Africa', 'Score': '0-1', 'Away Team': 'Canada'}
    ]

    gen_tuple = display_stage_results(mock_match_tuple)
    gen_invalid = display_stage_results(mock_match_invalid_dict)


    with pytest.raises(TypeError):
        next(gen_tuple) # Raises TypeError If data is not list of dict.

    with pytest.raises(KeyError):
        next(gen_invalid) # Raises KeyError if data not containing important key 'Stage'.



def test_process_player_stats_success(fifa_worldcup_save):

    sample_data = fifa_worldcup_save['player_data']

    results = process_player_stats(sample_data)

    assert isinstance(results, tuple) and isinstance(results[0], list) and isinstance(results[1], list)
    assert [item for item in results[0][0]] == ['player', 'team_country', 'minutes', 'goals', 'assists']

    assert results[0][0]['player'] == "Adil Boulbina" and results[0][0]['team_country'] == "Algeria"
    assert results[0][0]['minutes'] == 19.0 and results[0][0]['goals'] != '0.0' and results[0][0]['assists'] == 0.0


    assert [keys for keys in results[1][0]] == ['player', 'team_country', 'gk_games', 'gk_minutes', 'gk_clean_sheets']
    assert results[1][1]['player'] == 'Oussama Benbot'

    assert results[1][1]['gk_minutes'] == 90.0 and results[1][1]['gk_games'] == 1.0 \
        and results[1][1]['gk_clean_sheets'] == 0.0


def test_process_player_stats_failured(caplog):

    incorrect_sample_data = load_file_data(player_url)['Results'][11]

    sample_data_incorrect_key = {'Results' : [{
        'player': 'Adil Boulbina', 'team_country': 'Algeria',
        'minutes': '19.0', 'goals': '0.0', 'assists': '0.0'
    }]}

    results_with_missing_key = process_player_stats(incorrect_sample_data) # if data doesn't contains 'Results' key.

    assert results_with_missing_key == ([], [])

    with caplog.at_level(logging.ERROR):
        with pytest.raises(KeyError):
            process_player_stats(sample_data_incorrect_key)

    assert ('logging_config', 40, "'gk_games' Something went wronge try again") in caplog.record_tuples



def test_get_top_scorers_success(fifa_worldcup_save):

    sample_data = fifa_worldcup_save['player_data']

    top_scorers = get_top_scorers(process_player_stats(sample_data), limit=2)

    assert isinstance(top_scorers, tuple) and len(top_scorers) == 2
    assert isinstance(top_scorers[0], list) and isinstance(top_scorers[1], list)
    assert len(top_scorers[0]) == 2 and len(top_scorers[1]) == 2

    assert top_scorers[0][0]['player'] == 'Lionel Messi' and top_scorers[0][0]['goals'] == 8.0
    assert top_scorers[0][1]['player'] == 'Vinicius Júnior' and top_scorers[0][1]['goals'] == 4.0

    assert top_scorers[1][0]['player'] == 'Camilo Vargas' and top_scorers[1][1]['player'] == 'Luca Zidane'
    assert top_scorers[1][0]['gk_clean_sheets'] == 4.0 and top_scorers[1][0]['gk_minutes'] == 480.0
    assert top_scorers[1][1]['gk_clean_sheets'] == 0.0 and top_scorers[1][1]['gk_minutes'] == 270.0



def test_get_top_scorers_failure(caplog):

    incorrect_data_keyerror = (
        [{'player': 'Lionel Messi', 'team_country': 'Argentina', 'minutes': 530.0, 'goals': 8.0, 'assists': 2.0}],
        [{'player': 'Camilo Vargas', 'team_country': 'Colombia', 'gk_games': 5.0}]
    )

    with caplog.at_level(logging.ERROR):

        with pytest.raises(TypeError):
            get_top_scorers(None)

        with pytest.raises(KeyError):
            get_top_scorers(incorrect_data_keyerror)

    assert all(
        log_tuple[2] in (
            'cannot unpack non-iterable NoneType object',
            "'gk_clean_sheets'",
        )
        for log_tuple in caplog.record_tuples
    )



@pytest.mark.parametrize("screen_type, expected_text",[
    ("1", [
            "FIFA WORLD CUP LIVE",
            'Status: No live mactches are currently in progress',
            'Please check back later during match hours'
        ]
    ),
    ("2", [
            'Position', 'Mexico', 'Switzerland','Brazil','USA', 'Germany',
            'Netherlands', 'France', 'Argentina', 'Colombia', 'England',
            'Group A', 'Group B', 'Group C', 'Group D', 'Group E', 'Group F',
            'Group G', 'Group H', 'Group I', 'Group J', 'Group K', 'Group L'
        ]
    ),
    ("4", [
            'Attackers Top Scores', 'Goalkeepers Top Scores', 'Lionel Messi',
            'Kylian Mbappé', 'Unai Simón', 'Emiliano Martínez', 'Colombia',
            'Norway', 'Harry Kane', '605', 'minutes', '630', 'gk_minutes',
        ]
    ),
    ( "3",[
            '''
    ╭────────────────────────────────────────────────────╮
    │                Completed Matches                   │
    ╰────────────────────────────────────────────────────╯''',
            '== ROUND OF 32 ==', "ROUND OF 16", "QUARTER-FINAL", "SEMI-FINAL",
            "BRONZE FINAL", "FINAL", 'Argentina', '2026-06-28', '2026-07-02',
            '73', '2026-06-28',  'Round of 32',  'South Africa',   '0-1', 'Canada',

            '\n==================== ROUND OF 32 ====================\n',
            '│  Match_No  │', '│    Stage    │', '│  Score  │', '│   Winner    │',
            '│    104     │', ' │ 2026-07-19 │', '│    Spain    │   1-0   │', '│  Argentina  │  Spain   │',
            '│    103     │ 2026-07-18 │ Bronze final │   France    │   4-6   │   England   │ England  │',

            '''\n==================== SEMI-FINAL ====================
┌────────────┬────────────┬────────────┬─────────────┬─────────┬─────────────┬───────────┐
│  Match_No  │    Date    │   Stage    │  Home Team  │  Score  │  Away Team  │  Winner   │
├────────────┼────────────┼────────────┼─────────────┼─────────┼─────────────┼───────────┤
│    101     │ 2026-07-14 │ Semi-final │   France    │   0-2   │    Spain    │   Spain   │
├────────────┼────────────┼────────────┼─────────────┼─────────┼─────────────┼───────────┤
│    102     │ 2026-07-15 │ Semi-final │   England   │   1-2   │  Argentina  │ Argentina │
└────────────┴────────────┴────────────┴─────────────┴─────────┴─────────────┴───────────┘\n''',

            '''\n==================== QUARTER-FINAL ====================
┌────────────┬────────────┬───────────────┬─────────────┬─────────┬─────────────┬───────────┐
│  Match_No  │    Date    │     Stage     │  Home Team  │  Score  │  Away Team  │  Winner   │
├────────────┼────────────┼───────────────┼─────────────┼─────────┼─────────────┼───────────┤
│     97     │ 2026-07-09 │ Quarter-final │   France    │   2-0   │   Morocco   │  France   │
├────────────┼────────────┼───────────────┼─────────────┼─────────┼─────────────┼───────────┤
│     98     │ 2026-07-10 │ Quarter-final │    Spain    │   2-1   │   Belgium   │   Spain   │
├────────────┼────────────┼───────────────┼─────────────┼─────────┼─────────────┼───────────┤
│     99     │ 2026-07-11 │ Quarter-final │   Norway    │   1-2   │   England   │  England  │
├────────────┼────────────┼───────────────┼─────────────┼─────────┼─────────────┼───────────┤
│    100     │ 2026-07-12 │ Quarter-final │  Argentina  │   3-1   │ Switzerland │ Argentina │
└────────────┴────────────┴───────────────┴─────────────┴─────────┴─────────────┴───────────┘\n''',
            '''
    ╭─────────────────────────────────────────────────────────╮
    │ Status: No Scheduled mactches are currently in progress │
    ╰─────────────────────────────────────────────────────────╯'''
        ]

    )
    ])
def test_build_terminal_dashboard_success(screen_type, expected_text, monkeypatch, capsys):

    if screen_type == "3":
        monkeypatch.setattr("builtins.input", lambda option="": "")

    build_terminal_dashboard(screen_type)

    captured = capsys.readouterr()

    for item in expected_text:
        assert item in captured.out



@pytest.mark.parametrize('user_input, expected_error, expected_text', [
    ('a', ValueError, '\nPlease type correct number..\n'),
    ('6', ValueError, '\nPlease type correct number..\n'),
    ('-5', ValueError,'\nPlease type correct number..\n'),

    ('5', EOFError, """
    ==================================================
         👋 Exiting FIFA World Cup Dashboard...
        Thank you for using the application! Goodbye! ⚽
    ==================================================\n""")
])
def test_build_terminal_dashboard_raises_err(user_input, expected_error, expected_text,capsys):

    with pytest.raises(expected_exception=expected_error):
        build_terminal_dashboard(user_input)

    captured = capsys.readouterr()

    assert expected_text == captured.out





# if __name__ == '__main__':   # For debuging purpose.
#     pytest.main(['-s', __file__])
