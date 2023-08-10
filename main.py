import argparse
import platform
import os
import sys
import requests
from urllib.error import HTTPError
import datetime as dt
from math import ceil
from ffb_class import League
from query import transaction_check, update_draft

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

def graphql_req(operation, league, player, slot = 0, value = 0):
    headers = {'Authorization': args['auth'],
               'Content-Type': 'application/json',
               'Accept': 'application/json'}
    if operation == 'league_transactions_by_player':
        body = transaction_check(operation, league, player)
        return (requests.request("POST", "https://sleeper.com/graphql", headers=headers, data=body)).json()
        
    elif operation == 'draft_force_auction_pick':
        body = update_draft(operation, player, args['draftid'], slot, value)
        requests.request("POST", "https://sleeper.com/graphql", headers=headers, data=body)

def mod_one_team(league, user_dict, roster, slotid, action):
    print(f"Modifying {user_dict['display_name']}")
    keepers = build_keeper_dict(league, roster, slotid, action)

    for keeper in keepers.items():
        print(keeper[1]['name'])
        graphql_req('draft_force_auction_pick', league, keeper[1]['player_id'], slotid, keeper[1]['value'])
        
    print(f"League member {user_dict['display_name']} keepers have been updated.")
        
def mod_all_teams(l, slotids, index = 0):
    print('Modifying all teams keeper values')
    keepers = {}
    for roster in l.rosters:
        slotid = list(slotids.keys())[list(slotids.values()).index(roster['roster_id'])]
        try:
            keepers[index] = build_keeper_dict(l.leagueid, roster, slotid, action='m')
            index = index + 1
        except:
            print('No keepers have been selected')
            continue
        
    for keeper in keepers.items():
        playerlist = list(keeper[1].keys())
        for player in playerlist:
            graphql_req('draft_force_auction_pick', l.leagueid, keeper[1][player]['player_id'], keeper[1][player]['slot_id'], keeper[1][player]['value'])        

def build_keeper_dict(league, roster, slotid, action):
    print('Building keeper list')
    keeper_dict = {}
    for keeper in roster['keepers']:
        keeper_info = get_sleeper_req('player', keeper)
        keeper_name = f"{keeper_info['first_name']} {keeper_info['last_name']}"
        keeper_tran = graphql_req('league_transactions_by_player', league, keeper)
        keeper_value = proc_trans(keeper_tran, keeper, action)
        keeper_dict[int(keeper)] =  {
                                    'name' : keeper_name,
                                    'roster_id' : roster['roster_id'],
                                    'slot_id' : slotid,
                                    'player_id' : keeper, 
                                    'value': keeper_value
                                    }
    
    return dict(keeper_dict)                              

def proc_trans(json, player, action, trans_value = None, index = -1):
    transactions = json['data']['league_transactions_by_player']
    print(f"{transactions[index]['player_map'][player]['first_name']} {transactions[index]['player_map'][player]['last_name']}")
    while trans_value == None:
        tran_date = dt.datetime.fromtimestamp(transactions[index]['status_updated']/1000)
        if transactions[index]['type'] == 'draft_pick' and tran_date < dt.datetime(2022, 8, 27):
            print('Original Seed Draft draft')
            index = index - 1
        elif transactions[index]['type'] == 'draft_pick':
            try:
                trans_value = transactions[index]['metadata']['amount']
                print('Draft pick')
            except:
                index = index -1
        elif transactions[index]['type'] == 'waiver':
            try:
                trans_value = transactions[index]['settings']['waiver_bid']
                print('Waiver Pickup')
            except:
                index = index - 1
        else:
            print('someone did something naughty')
            index = index - 1
            
    new_value = ceil((float(trans_value) * 1.1) + 5)
    print(f'Here is the current salary: {trans_value}')
    print(f'Here is the new salary: {new_value}')
    
    if action == 'm':
        return new_value
    elif action == 't':
        return ''
         
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

def get_team_info(l, action, roster_dict = {}):
    for roster in l.rosters:
        roster_dict[roster["owner_id"]] = roster
        
    print('Here are all the team names and IDs')
    for user in l.users:
        print(f"User name, User id: {user['display_name']}, {user['user_id']}")
        
    user_id = input('What roster would you like to look up? [User id]: \n')

    for player in roster_dict[user_id]['players']:
        player_info = get_sleeper_req('player', player)
        keeper_tran = graphql_req('league_transactions_by_player', l.leagueid, player)
        print(
f"""\
Postion: {player_info['position']}
{proc_trans(keeper_tran, player, action)}\
""")
    print('Keepers')
    for keeper in roster_dict[user_id]['keepers']:
        keeper_info = get_sleeper_req('player', keeper)
        print(f"Postion: {keeper_info['position']}, Name: {keeper_info['first_name']} {keeper_info['last_name']}")
        
def mod_league(l, modify = '', roster_dict = {}):
    slot_to_roster = l.draft['slot_to_roster_id']
    print('Building roster list')
    for roster in l.rosters:
        roster_dict[int(roster['owner_id'])] = roster
        
    while modify not in ('a','o','x'):
        modify = input('Do you want to modify [a]ll teams, [o]ne team, or e[x]it? \n').lower()
        if modify == 'x':
            break
        elif modify == 'a':
            mod_all_teams(l, slot_to_roster)    
            print('All keepers have been updated')        
        elif modify == 'o':
            print('Modifying a single team')
            print('Here are all the team names and IDs')    
            user_dict = {}
            for user in l.users:
                user_dict[int(user['user_id'])] = {
                    'id': user['user_id'],
                    'display_name': user['display_name']
                }
                print(f"User name, User id: {user['display_name']}, {user['user_id']}")
                    
            user_id = int(input("Who's keepers would you like to modify? [User id]: \n"))            
            roster = roster_dict[user_id]
            slotid = list(slot_to_roster.keys())[list(slot_to_roster.values()).index(roster['roster_id'])]
            mod_one_team(l.leagueid, user_dict[user_id], roster, slotid, action)
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
        l = League(args['leagueid'], draft)
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
            get_team_info(l, action)
        elif action == 'm':
            print('Modifying League')
            mod_league(l, action)