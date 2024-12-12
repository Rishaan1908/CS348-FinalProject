from datetime import datetime
import random
from database_setup import Session, Game, GameLineup, PlayerGameStat, Player, Team

def simulate_player_performance(player, minutes_played, is_starter=False, is_home_team=False, randomness_factor=0.2, performance_boost=1.0):
    """Simulate a player's performance based on their averages and minutes played."""
    # Base multiplier for minutes played 
    minutes_multiplier = minutes_played / 48.0
    
    # (5% boost for home team)
    home_advantage = 1.05 if is_home_team else 1.0
    
    # (15% boost for starters)
    starter_boost = 1.15 if is_starter else 0.85
    
    # (-20% to +20% by default)
    random_multiplier = 1.0 + random.uniform(-randomness_factor, randomness_factor)
    
    # Combine all multipliers including performance boost
    performance_multiplier = minutes_multiplier * random_multiplier * home_advantage * starter_boost * performance_boost
    
    # Calculate attempted field goals based on average points and FG percentage
    avg_fga = (player.avg_points / 2) / (player.fg_percentage if player.fg_percentage > 0 else 0.4)
    
    fga = round(avg_fga * performance_multiplier)
    fgm = round(fga * player.fg_percentage * random_multiplier)
    
    # Adjust points calculation
    points = round(player.avg_points * performance_multiplier)
    
    return {
        'points': points,
        'rebounds': round(player.avg_rebounds * performance_multiplier),
        'assists': round(player.avg_assists * performance_multiplier),
        'steals': round(player.avg_steals * performance_multiplier),
        'blocks': round(player.avg_blocks * performance_multiplier),
        'turnovers': round(player.avg_turnovers * performance_multiplier),
        'fouls': min(6, round(player.avg_fouls * performance_multiplier)),
        'fgm': fgm,
        'fga': fga,
        'minutes_played': minutes_played
    }

def allocate_minutes(starters, bench):
    """
    Allocate minutes to players based on starter status.
    Ensures total team minutes equals 240 (48 minutes × 5 players)
    """
    total_game_minutes = 240  # 48 minutes × 5 players
    minutes_allocation = {}
    
    # Base minutes for starters and bench
    base_starter_minutes = 30
    base_bench_minutes = 15
    
    # First, allocate base minutes to starters
    remaining_minutes = total_game_minutes
    for starter in starters:
        minutes = base_starter_minutes + random.uniform(-3, 3)
        minutes_allocation[starter.player_id] = minutes
        remaining_minutes -= minutes
    
    # Then allocate minutes to bench players
    if bench:  # Only if there are bench players
        base_bench_per_player = remaining_minutes / len(bench)
        
        for bench_player in bench:
            # For the last bench player, use remaining minutes exactly
            if bench_player == bench[-1]:
                minutes_allocation[bench_player.player_id] = remaining_minutes
            else:
                minutes = min(base_bench_per_player + random.uniform(-2, 2), remaining_minutes)
                minutes_allocation[bench_player.player_id] = minutes
                remaining_minutes -= minutes
    
    # Ensure no negative minutes and round to 1 decimal
    for player_id in minutes_allocation:
        minutes_allocation[player_id] = round(max(minutes_allocation[player_id], 0), 1)
    
    return minutes_allocation

def simulate_game(home_players, away_players, arena="Home Arena", resimulate_id=None, is_season_game=False, season_id=None, favorite_team_boost=False):
    """
    Simulate a game with the selected players.
    
    Parameters:
    - home_players: list of player IDs for home team
    - away_players: list of player IDs for away team
    - arena: string, name of the arena
    - resimulate_id: int, game ID if resimulating an existing game
    - is_season_game: bool, whether this is part of season simulation
    - season_id: int, identifier for the season
    - favorite_team_boost: bool, whether to apply favorite team boost
    """
    session = Session()
    
    try:
        # Get player objects - all players, not just starters
        home_starters = session.query(Player).filter(Player.player_id.in_(home_players[:5])).all()
        home_bench = session.query(Player).filter(Player.player_id.in_(home_players[5:])).all()
        away_starters = session.query(Player).filter(Player.player_id.in_(away_players[:5])).all()
        away_bench = session.query(Player).filter(Player.player_id.in_(away_players[5:])).all()

        if not (home_starters and away_starters):
            raise ValueError("Could not find all selected players")
            
        if len(home_starters) != 5 or len(away_starters) != 5:
            raise ValueError("Need exactly 5 starters per team")
        # Create or update game record
        if resimulate_id:
            game = session.query(Game).filter_by(game_id=resimulate_id).first()
            if game:
                game.resimulated = True
                game.game_date = datetime.now().date()
                game.game_time = datetime.now().time()
            else:
                raise ValueError(f"Game with ID {resimulate_id} not found")
        else:
            game = Game(
                game_date=datetime.now().date(),
                game_time=datetime.now().time(),
                resimulated=False,
                arena=arena,
                home_team_id=home_starters[0].team_id,
                away_team_id=away_starters[0].team_id,
                is_season_game=is_season_game,
                season_id=season_id
            )
            session.add(game)
        
        session.flush()
        
        # Allocate minutes for both teams
        home_minutes = allocate_minutes(home_starters, home_bench)
        away_minutes = allocate_minutes(away_starters, away_bench)
        
        # Apply favorite team boost if needed
        performance_boost = 1.05 if favorite_team_boost else 1.0
        
        # Simulate individual performances
        home_stats = {}
        away_stats = {}
        
        # Process all home team players (starters and bench)
        for player in home_starters + home_bench:
            is_starter = player in home_starters
            minutes = home_minutes[player.player_id]
            
            # Only create stats if player played minutes
            if minutes > 0:
                lineup = GameLineup(
                    is_starter=is_starter,
                    minutes_played=minutes,
                    game_id=game.game_id,
                    team_id=player.team_id,
                    player_id=player.player_id
                )
                session.add(lineup)
                
                stats = simulate_player_performance(
                    player, 
                    minutes,
                    is_starter=is_starter,
                    is_home_team=True,
                    performance_boost=performance_boost if favorite_team_boost else 1.0
                )
                home_stats[player.player_id] = stats
                
                player_stats = PlayerGameStat(
                    game_id=game.game_id,
                    player_id=player.player_id,
                    **stats
                )
    
                session.add(player_stats)
        
        # Process all away team players (starters and bench)
        for player in away_starters + away_bench:
            is_starter = player in away_starters
            minutes = away_minutes[player.player_id]
            
            if minutes > 0:
                lineup = GameLineup(
                    is_starter=is_starter,
                    minutes_played=minutes,
                    game_id=game.game_id,
                    team_id=player.team_id,
                    player_id=player.player_id
                )
                session.add(lineup)
                
                stats = simulate_player_performance(
                    player, 
                    minutes,
                    is_starter=is_starter,
                    is_home_team=False,
                    performance_boost=performance_boost if favorite_team_boost else 1.0
                )
                away_stats[player.player_id] = stats
                
                player_stats = PlayerGameStat(
                    game_id=game.game_id,
                    player_id=player.player_id,
                    **stats
                )
                session.add(player_stats)

        # Update game score
        game.home_team_score = sum(stats['points'] for stats in home_stats.values())
        game.away_team_score = sum(stats['points'] for stats in away_stats.values())

        session.commit()
        
        return {
            'game_id': game.game_id,
            'home_team': {
                'team_id': home_starters[0].team_id,
                'score': game.home_team_score,
                'players': home_stats
            },
            'away_team': {
                'team_id': away_starters[0].team_id,
                'score': game.away_team_score,
                'players': away_stats
            }
        }
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()