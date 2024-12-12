# team_stats.py
from sqlalchemy import func, desc
from database_setup import Session, Team, Game, Player, PlayerGameStat

def update_team_records():
    """Update win/loss records and stats for all teams"""
    session = Session()
    try:
        teams = session.query(Team).all()
        
        for team in teams:
            # Get all home and away games
            home_games = session.query(Game).filter(Game.home_team_id == team.team_id).all()
            away_games = session.query(Game).filter(Game.away_team_id == team.team_id).all()
            
            wins = 0
            total_points = 0
            games_played = len(home_games) + len(away_games)
            
            # Process home games
            for game in home_games:
                if game.home_team_score > game.away_team_score:
                    wins += 1
                total_points += game.home_team_score
                
            # Process away games
            for game in away_games:
                if game.away_team_score > game.home_team_score:
                    wins += 1
                total_points += game.away_team_score
            
            # Update team stats
            if games_played > 0:
                team.win_rate = wins / games_played
                team.avg_points = total_points / games_played
            
            session.add(team)
        
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_standings():
    """Get current standings organized by conference and division"""
    session = Session()
    try:
        teams = session.query(Team).order_by(
            Team.conference,
            Team.division,
            desc(Team.win_rate)
        ).all()
        
        standings = {}
        for team in teams:
            if team.conference not in standings:
                standings[team.conference] = {}
            
            if team.division not in standings[team.conference]:
                standings[team.conference][team.division] = []
            
            # Get team's stats
            home_games = session.query(Game).filter(Game.home_team_id == team.team_id)
            away_games = session.query(Game).filter(Game.away_team_id == team.team_id)
            
            games_played = home_games.count() + away_games.count()
            wins = 0
            losses = 0
            
            for game in home_games:
                if game.home_team_score > game.away_team_score:
                    wins += 1
                else:
                    losses += 1
                    
            for game in away_games:
                if game.away_team_score > game.home_team_score:
                    wins += 1
                else:
                    losses += 1
            
            team_data = {
                'team_id': team.team_id,
                'name': f"{team.city} {team.team_name}",
                'wins': wins,
                'losses': losses,
                'win_rate': team.win_rate,
                'games_played': games_played,
                'avg_points': team.avg_points if hasattr(team, 'avg_points') else 0
            }
            
            standings[team.conference][team.division].append(team_data)
        
        return standings
    finally:
        session.close()

def get_team_stats(team_id):
    """Get detailed statistics for a specific team"""
    session = Session()
    try:
        team = session.query(Team).get(team_id)
        if not team:
            return None
            
        # Get all games
        home_games = session.query(Game).filter(Game.home_team_id == team_id)
        away_games = session.query(Game).filter(Game.away_team_id == team_id)
        
        # Calculate stats
        home_stats = home_games.with_entities(
            func.avg(Game.home_team_score).label('avg_points'),
            func.max(Game.home_team_score).label('max_points'),
            func.count().label('games')
        ).first()
        
        away_stats = away_games.with_entities(
            func.avg(Game.away_team_score).label('avg_points'),
            func.max(Game.away_team_score).label('max_points'),
            func.count().label('games')
        ).first()
        
        total_games = (home_stats.games or 0) + (away_stats.games or 0)
        avg_points = 0
        if total_games > 0:
            total_points = (
                (home_stats.avg_points or 0) * (home_stats.games or 0) +
                (away_stats.avg_points or 0) * (away_stats.games or 0)
            )
            avg_points = total_points / total_games
            
        return {
            'team_name': f"{team.city} {team.team_name}",
            'games_played': total_games,
            'avg_points': round(avg_points, 1),
            'max_points': max(home_stats.max_points or 0, away_stats.max_points or 0),
            'home_record': {
                'games': home_stats.games or 0,
                'avg_points': round(home_stats.avg_points or 0, 1)
            },
            'away_record': {
                'games': away_stats.games or 0,
                'avg_points': round(away_stats.avg_points or 0, 1)
            }
        }
    finally:
        session.close()