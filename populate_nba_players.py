from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playercareerstats
from database_setup import Session, Player, Team
import time

def get_player_career_averages(player_id):
    """Get per-game career averages for a player, rounded to 1 decimal point."""
    try:
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        career_data = career_stats.get_data_frames()[0]
        
        if not career_data.empty:
            # Check if there's a row for career totals or averages
            if 'CAREER' in career_data['SEASON_ID'].values:
                career_row = career_data[career_data['SEASON_ID'] == 'CAREER'].iloc[0]
            else:
                # Calculate averages manually if "CAREER" row is unavailable
                career_row = career_data.mean(numeric_only=True)
            
            # Calculate per-game averages and round to 1 decimal point
            games_played = career_row['GP'] if 'GP' in career_row else career_row['G']
            if games_played > 0:
                return {
                    'avg_points': round(career_row['PTS'] / games_played, 1),
                    'avg_rebounds': round(career_row['REB'] / games_played, 1),
                    'avg_assists': round(career_row['AST'] / games_played, 1),
                    'avg_steals': round(career_row['STL'] / games_played, 1),
                    'avg_blocks': round(career_row['BLK'] / games_played, 1),
                    'avg_turnovers': round(career_row['TOV'] / games_played, 1),
                    'avg_fouls': round(career_row['PF'] / games_played, 1),
                    'fg_percentage': round(career_row['FG_PCT'], 1)  # FG% is already a per-game stat
                }
    except Exception as e:
        print(f"Error getting career stats for player {player_id}: {e}")
    
    # Default values if stats cannot be fetched
    return {
        'avg_points': 0.0,
        'avg_rebounds': 0.0,
        'avg_assists': 0.0,
        'avg_steals': 0.0,
        'avg_blocks': 0.0,
        'avg_turnovers': 0.0,
        'avg_fouls': 0.0,
        'fg_percentage': 0.0
    }

def populate_current_nba_players():
    session = Session()
    nba_teams = teams.get_teams()
    
    # Clear existing players
    print("Clearing existing player data...")
    session.query(Player).delete()
    session.commit()
    
    total_players = 0
    for nba_team in nba_teams:
        print(f"\nProcessing team: {nba_team['full_name']}")
        
        team = session.query(Team).filter_by(team_name=nba_team['nickname']).first()
        if not team:
            print(f"Team {nba_team['nickname']} not found in database - skipping")
            continue
        
        try:
            roster = commonteamroster.CommonTeamRoster(team_id=nba_team['id'])
            roster_df = roster.get_data_frames()[0]
            
            team_player_count = 0
            for _, player_row in roster_df.iterrows():
                time.sleep(1)  # Rate limiting
                
                career_stats = get_player_career_averages(player_row['PLAYER_ID'])
                
                try:
                    player_data = {
                        'first_name': player_row['PLAYER'].split()[0],
                        'last_name': ' '.join(player_row['PLAYER'].split()[1:]),
                        'position': player_row['POSITION'],
                        'height': float(player_row['HEIGHT'].split('-')[0]) + float(player_row['HEIGHT'].split('-')[1])/10,
                        'weight': float(player_row['WEIGHT']),
                        'jersey_number': int(player_row['NUM']) if player_row['NUM'].isdigit() else 0,
                        'team_id': team.team_id,
                        **career_stats
                    }
                    
                    player = Player(**player_data)
                    session.add(player)
                    team_player_count += 1
                    total_players += 1
                    
                    print(f"Added player: {player_data['first_name']} {player_data['last_name']} "
                          f"(#{player_data['jersey_number']}) - {player_data['position']} - "
                          f"{player_data['avg_points']} PPG")
                    
                    # Commit after each player to avoid large transactions
                    session.commit()
                    
                except Exception as e:
                    print(f"Error adding player {player_row['PLAYER']}: {e}")
                    session.rollback()
                    continue
            
            print(f"Successfully added {team_player_count} players for {nba_team['full_name']}")
            
        except Exception as e:
            print(f"Error processing team {nba_team['full_name']}: {e}")
            continue
        
        time.sleep(2)  # Rate limiting between teams
    
    session.close()
    print(f"\nFinished! Added {total_players} players across all NBA teams.")

if __name__ == "__main__":
    print("Starting player database population...")
    start_time = time.time()
    
    populate_current_nba_players()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    print(f"\nTotal time taken: {minutes} minutes and {seconds} seconds")