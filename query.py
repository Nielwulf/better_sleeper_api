import json

transaction = """
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
    
draft = """
        draft_id
        pick_no
        player_id
        picked_by
        is_keeper
        metadata
      ]
    ]
    """
  
def update_draft(operation, player, draft, slot, value):
  query_line = f'mutation {operation} [\n       {operation}(sport: \"nfl\", player_id: \"{player}\", draft_id: \"{draft}\", slot: \"{slot}\", amount: \"{value}\", is_keeper: true)]'
  query_line = query_line + draft
  query_line = query_line.replace("[","{")
  query_line = query_line.replace("]","}")
  return json.dumps({
      'operationName': operation,
      'variables': {},
      'query': query_line
  })

def transaction_check(operation, league, player):
  query_line = f'query {operation} [\n        {operation}(league_id: \"{league}\", player_id: \"{player}\")['
  query_line = query_line + transaction
  query_line = query_line.replace("[","{")
  query_line = query_line.replace("]","}")
  return json.dumps({
      'operationName': operation,
      'variables': {},
      'query': query_line
  })