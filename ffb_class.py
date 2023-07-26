from sleeperpy import Leagues, Drafts

class League(object):
    def __init__(self, league, drafts):
        self.league_info = Leagues.get_league(league)
        self.rosters = Leagues.get_rosters(league)
        self.draft = Drafts.get_specific_draft(drafts)
        self.users = Leagues.get_users(league)
        
