from sleeperpy import Leagues, Drafts
import argparse
import platform
import os
import sys
import requests
from urllib.error import HTTPError
import json
from math import ceil

if platform.system() == "Windows": os.system('cls')
ap = argparse.ArgumentParser(description='App with a deeper Sleeper API integration.')
ap._action_groups.pop()
required = ap.add_argument_group('required arguments')
optional = ap.add_argument_group('optional arguments')
required.add_argument('-a', '--auth', type=str, required=True, help='Authentication needed to edit ANY Sleeper platform information.')
required.add_argument('-l', '--leagueid', type=str, required=True, help='The numerical Sleeper league ID you wish to read/write.')
required.add_argument('-d', '--draftid', type=str, required=True, help="This season's Draft ID.")
optional.add_argument('-m', '--modify', action="store_true", required=False, default=False, help='Flag needed if you plan to make changes.')
args = vars(ap.parse_args())

def get_action(modify, action):
    print('What would you like to do?\n')
    if modify != True:
        action = input('get [t]eam info, e[x]it:\n').lower()
    else:
        action = input('get [t]eam info, [m]odify league, e[x]it:\n').lower()
    
    return action

def get_league_info(league, drafts):
    league_info = Leagues.get_league(league)
    rosters = Leagues.get_rosters(league)
    draft = Drafts.get_specific_draft(drafts)
    users = Leagues.get_users(league) 
    return league_info, rosters, users, draft


def draft_graphql_req(player, value):
    print('help')

def value_graphql_req(operation, league, player):
    headers = {'Authorization': args['auth'],
               'Content-Type': 'application/json',
               'Accept': 'application/json'}
    query_line = f'query {operation} [\n        {operation}(league_id: \"{league}\", player_id: \"{player}\")['
    schema = """
          adds
          consenter_ids
          created
          creator
          drops
          league_id
          leg
          metadata
          roster_ids
          settings
          status
          status_updated
          transaction_id
          draft_picks
          type
          player_map
          waiver_budget
        ]
    ]
    """
    query_line = query_line + schema
    query_line = query_line.replace("[","{")
    query_line = query_line.replace("]","}")
    body = json.dumps({
        'operationName': operation,
        'variables': {},
        'query': query_line
    })
    r = requests.request("POST", "https://sleeper.com/graphql", headers=headers, data=body)
    keep_json = r.json()
    trans_value = None
    index = 0
    while trans_value == None:
        if keep_json['data']['league_transactions_by_player'][index]['type'] == 'waiver':
            try:
                trans_value = keep_json['data']['league_transactions_by_player'][index]['settings']['waiver_bid']
            except TypeError:
                print('Most recent transaction was a trade, checking next transaction.')
                index = index + 1
                
            except HTTPError as e:
                print(e)
        else:
            try:
                trans_value = keep_json['data']['league_transactions_by_player'][index]['metadata']['amount']
            except TypeError as e:
                print(e)
                index = index + 1
                
            except HTTPError as e:
                print('some sort of HTTP Error')
                print(e)
                
    print(f"{keep_json['data']['league_transactions_by_player'][index]['player_map'][player]['first_name']} {keep_json['data']['league_transactions_by_player'][index]['player_map'][player]['last_name']}")
    print(f'Here is the current salary: {trans_value}')
    new_value = ceil((float(trans_value) * 1.1) + 5)
    print(f'Here is the new salary: {new_value}')
    return new_value    
         
def get_sleeper_req(request_type, player):
    headers = {'Authorization': args['auth']}
    if request_type == 'player':
        r = requests.get(f'https://api.sleeper.com/players/nfl/{player}', headers=headers)
        try:
            r.raise_for_status()
        except HTTPError as http_err:
            print(f'HTTP error occured: {http_err}')
            sys.exit(1)
        except Exception as err:
            print(f'Other error occured: {err}')
            sys.exit(1)
        else:
            return r.json()

def get_team_info(rosters, users, roster_dict = {}):
    for roster in rosters:
        roster_dict[roster["owner_id"]] = roster
        
    print('Here are all the team names and IDs')
    for user in users:
        print(f"User name, User id: {user['display_name']}, {user['user_id']}")
        
    user_id = input('What roster would you like to look up? [User id]: \n')

    for player in roster_dict[user_id]['players']:
        player_info = get_sleeper_req('player', player)
        print(f"Postion: {player_info['position']}, Name: {player_info['first_name']} {player_info['last_name']}")
    print('Keepers')
    for keeper in roster_dict[user_id]['keepers']:
        keeper_info = get_sleeper_req('player', keeper)
        print(f"Postion: {keeper_info['position']}, Name: {keeper_info['first_name']} {keeper_info['last_name']}")
        
def mod_league(rosters, users, league, draft, modify = ''):
    slot_to_roster = draft['slot_to_roster_id']
    while modify not in ('a','o','x'):
        modify = input('Do you want to modify [a]ll teams or [o]ne team? \n').lower()
        if modify == 'x':
            break
        elif modify == 'a':
            print('All teams')            
        elif modify == 'o':
            print('One team')
            roster_dict = {}
            for roster in rosters:
                roster_dict[int(roster["owner_id"])] = roster
                
            print('Here are all the team names and IDs')
            for user in users:
                print(f"User name, User id: {user['display_name']}, {user['user_id']}")
                
            user_id = int(input("Who's keepers would you like to modify? [User id]: \n"))
            keeper_dict = {}
            for keeper in roster_dict[user_id]['keepers']:
                keeper_info = get_sleeper_req('player', keeper)
                keeper_name = f"{keeper_info['first_name']} {keeper_info['last_name']}"
                keeper_dict[keeper_name] = {'roster_id': roster_dict[user_id]['roster_id'],
                                            'slot_id': list(slot_to_roster.keys())[list(slot_to_roster.values()).index(roster_dict[user_id]['roster_id'])],
                                            'player_id': keeper, 
                                            'value': value_graphql_req('league_transactions_by_player', league, keeper)}
                
            print(keeper_dict)
        
        else:
            print('Please select [a]ll, [o]ne team, e[x]it')
        
    
if __name__ == "__main__":
    try: 
        auth = args['auth']
        print('Authorization credentials have been provided.')
    except:
        print('Authorization credentials have not been provided, follow the instructions in the README on how to get it.')
        sys.exit(1)
        
    try:
        draft = args['draftid']
        print(f"This year's draft id: {draft}")
    except:
        draft = input("What is this year's draft ID?")
    
    try:
        modify = args['modify']
    except:
        print('No settings or attributes will be modified')
    
    try:
        print(f"League ID has been provided: {args['leagueid']}")
        league, rosters, users, drafts = get_league_info(args['leagueid'], draft)
    except:
        print('No league ID has been provided')
        sys.exit(1)
        
    action = ''
    while action != 'x':
        action = get_action(modify, action)
    
        if action == 'x':
            print('Thanks for using the app, closing now')
            sys.exit(0)
        elif action =='t':
            print('getting Team info')
            get_team_info(rosters, users)
        elif action == 'm':
            print('Modifying League')
            mod_league(rosters, users, args['leagueid'], drafts)