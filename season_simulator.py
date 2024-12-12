# season_simulator.py
from datetime import datetime, timedelta
import random
import json
from database_setup import Session, Team, Player
from game_simulator import simulate_game

def generate_favorite_team_schedule(favorite_team_id, games_count=82):
    session = Session()
    try:
        favorite_team = session.query(Team).get(favorite_team_id)
        print(f"Generating schedule for {favorite_team.city} {favorite_team.team_name}")
        
        # Get all potential opponents
        all_teams = session.query(Team).filter(Team.team_id != favorite_team_id).all()
        
        # Get teams from same conference for balanced scheduling
        conference_teams = [team for team in all_teams if team.conference == favorite_team.conference]
        other_teams = [team for team in all_teams if team.conference != favorite_team.conference]
        
        schedule = []
        
        # Conference games (more frequent)
        conference_games = games_count // 2  # About half the games should be conference games
        
        # Home conference games
        for _ in range(conference_games // 2):
            opponent = random.choice(conference_teams)
            schedule.append((favorite_team_id, opponent.team_id))
            
        # Away conference games
        for _ in range(conference_games // 2):
            opponent = random.choice(conference_teams)
            schedule.append((opponent.team_id, favorite_team_id))
            
        # Non-conference games
        remaining_games = games_count - conference_games
        
        # Home non-conference games
        for _ in range(remaining_games // 2):
            opponent = random.choice(other_teams)
            schedule.append((favorite_team_id, opponent.team_id))
            
        # Away non-conference games
        for _ in range(remaining_games // 2):
            opponent = random.choice(other_teams)
            schedule.append((opponent.team_id, favorite_team_id))
            
        random.shuffle(schedule)  # Randomize game order
        return schedule
    finally:
        session.close()
   
def get_team_season_mvp(team_id):
    """Get the MVP (best performer) from a specific team"""
    session = Session()
    try:
        players = session.query(Player)\
            .filter_by(team_id=team_id)\
            .filter(Player.season_games > 0)\
            .all()
            
        if not players:
            return None
            
        # Calculate MVP score for each player
        mvp_candidates = []
        for player in players:
            mvp_score = (player.season_ppg * 1.0 + 
                        player.season_rpg * 0.8 + 
                        player.season_apg * 1.2)
            mvp_candidates.append((player, mvp_score))
        
        if mvp_candidates:
            mvp_candidates.sort(key=lambda x: x[1], reverse=True)
            return mvp_candidates[0]
            
        return None
    finally:
        session.close()