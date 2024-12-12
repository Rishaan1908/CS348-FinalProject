from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from database_setup import Session, Player, Team, Game, GameLineup, PlayerGameStat, get_all_teams
from sqlalchemy.ext.declarative import DeclarativeMeta
from urllib.parse import parse_qs, urlparse
from game_simulator import simulate_game
from datetime import datetime, date, time
from sqlalchemy import or_, func
from datetime import datetime, timedelta
from team_stats import get_team_stats
from season_simulator import (
    generate_favorite_team_schedule, 
    get_team_season_mvp, 
)


class DatabaseJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        return super().default(obj)

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Handle API endpoints
        if path == '/get_teams':
            self._handle_get_teams()
        elif path.startswith('/get_team_players/'):
            self._handle_get_team_players()
        elif path == '/get_games':
            self._handle_get_games()
        elif path.startswith('/team_info/'):
            self._handle_team_info()
        elif path.startswith('/season_mvp/'):
            self._handle_season_mvp()
        elif path.startswith('/game_result/'):
            self._handle_get_game_result()
        elif path.startswith('/team_schedule/'):
            self._handle_team_schedule()
        # Handle static files
        elif path == '/':
            self._serve_file('index.html')
        elif path in ['/index.html', '/lineups.html', '/game_result.html', 
                    '/game_history.html', '/season_setup.html', '/season_results.html', '/single_game.html']:
            self._serve_file(path[1:])
        else:
            self.send_error(404)

    def _handle_get_teams(self):
        """Handle /get_teams endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        teams = get_all_teams()
        teams_json = json.dumps(teams, cls=DatabaseJSONEncoder)
        self.wfile.write(teams_json.encode())

    def _handle_get_team_players(self):
        """Handle /get_team_players/<team_id> endpoint"""
        try:
            team_id = int(self.path.split('/')[-1])
            session = Session()
            
            # Modified query to order players by average points descending
            players = session.query(Player)\
                .filter_by(team_id=team_id)\
                .order_by(Player.avg_points.desc())\
                .all()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            players_json = json.dumps(players, cls=DatabaseJSONEncoder)
            self.wfile.write(players_json.encode())
        except ValueError as e:
            print(f"Invalid team ID: {str(e)}")
            self.send_error(400, "Invalid team ID")
        except Exception as e:
            print(f"Error getting team players: {str(e)}")
            self.send_error(500, str(e))
        finally:
            session.close()

    def _handle_team_stats(self):
        """Handle /team_stats/<team_id> endpoint"""
        try:
            team_id = int(self.path.split('/')[-1])
            stats = get_team_stats(team_id)
            
            if not stats:
                self.send_error(404, "Team not found")
                return
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats, cls=DatabaseJSONEncoder).encode())
        except Exception as e:
            print(f"Error getting team stats: {str(e)}")
            self.send_error(500, str(e))
            
    def _handle_get_games(self):
        """Handle /get_games endpoint"""
        session = Session()
        try:
            games = session.query(Game)\
            .filter(Game.is_season_game == False)\
            .order_by(Game.game_date.desc(), Game.game_time.desc())\
            .all()
            results = []
            
            for game in games:
                home_team = session.get(Team, game.home_team_id)
                away_team = session.get(Team, game.away_team_id)
                
                home_stats = session.query(PlayerGameStat, Player).join(Player).filter(
                    PlayerGameStat.game_id == game.game_id,
                    Player.team_id == game.home_team_id
                ).all()
                
                away_stats = session.query(PlayerGameStat, Player).join(Player).filter(
                    PlayerGameStat.game_id == game.game_id,
                    Player.team_id == game.away_team_id
                ).all()
                
                game_data = {
                    'game': {
                        'game_id': game.game_id,
                        'home_score': game.home_team_score,
                        'away_score': game.away_team_score,
                        'date': game.game_date,
                        'time': game.game_time,
                        'arena': game.arena,
                        'resimulated': game.resimulated
                    },
                    'home_team': {
                        'team_id': home_team.team_id,
                        'name': f"{home_team.city} {home_team.team_name}",
                        'players': [{
                            'name': f"{player.first_name} {player.last_name}",
                            'position': player.position,
                            'jersey_number': player.jersey_number,
                            'stats': {
                                'points': stat.points,
                                'rebounds': stat.rebounds,
                                'assists': stat.assists,
                                'steals': stat.steals,
                                'blocks': stat.blocks,
                                'turnovers': stat.turnovers,
                                'fouls': stat.fouls,
                                'fgm': stat.fgm,
                                'fga': stat.fga,
                                'minutes': stat.minutes_played
                            }
                        } for stat, player in home_stats]
                    },
                    'away_team': {
                        'team_id': away_team.team_id,
                        'name': f"{away_team.city} {away_team.team_name}",
                        'players': [{
                            'name': f"{player.first_name} {player.last_name}",
                            'position': player.position,
                            'jersey_number': player.jersey_number,
                            'stats': {
                                'points': stat.points,
                                'rebounds': stat.rebounds,
                                'assists': stat.assists,
                                'steals': stat.steals,
                                'blocks': stat.blocks,
                                'turnovers': stat.turnovers,
                                'fouls': stat.fouls,
                                'fgm': stat.fgm,
                                'fga': stat.fga,
                                'minutes': stat.minutes_played
                            }
                        } for stat, player in away_stats]
                    }
                }
                results.append(game_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results, cls=DatabaseJSONEncoder).encode())
            
        except Exception as e:
            print(f"Error getting games: {str(e)}")
            self.send_error(500, str(e))
        finally:
            session.close()
    
    def _handle_team_schedule(self):
        """Handle GET request for team's season schedule"""
        try:
            team_id = int(self.path.split('/')[-1])
            session = Session()
            
            # Get team info
            team = session.query(Team).get(team_id)
            if not team:
                self.send_error(404, "Team not found")
                return
                
            print(f"Getting schedule for {team.city} {team.team_name}")
            
            # Get all season games for this team
            games = session.query(Game)\
                .filter(
                    Game.is_season_game == True,
                    or_(Game.home_team_id == team_id, Game.away_team_id == team_id)
                )\
                .all()
                
            print(f"Found {len(games)} games")
            
            schedule = []
            for game in games:
                # Get the opponent team
                if game.home_team_id == team_id:
                    opponent_team = session.query(Team).get(game.away_team_id)
                    is_home = True
                    team_score = game.home_team_score
                    opponent_score = game.away_team_score
                else:
                    opponent_team = session.query(Team).get(game.home_team_id)
                    is_home = False
                    team_score = game.away_team_score
                    opponent_score = game.home_team_score
                
                is_conference = team.conference == opponent_team.conference
                
                game_data = {
                    'date': game.game_date.isoformat(),
                    'opponent': f"{opponent_team.city} {opponent_team.team_name}",
                    'isHome': is_home,
                    'teamScore': team_score,
                    'opponentScore': opponent_score,
                    'isWin': team_score > opponent_score,
                    'isConferenceGame': is_conference,
                    'arena': game.arena
                }
                
                print(f"Game data: {game_data}")
                schedule.append(game_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(schedule).encode())
            
        except Exception as e:
            print(f"Error getting team schedule: {e}")
            self.send_error(500, str(e))
        finally:
            session.close()

    def _handle_get_game_lineups(self):
        """Handle /get_game_lineups/<game_id> endpoint"""
        try:
            game_id = int(self.path.split('/')[-1])
            session = Session()

            lineups = session.query(GameLineup, Player).join(
                Player,
                GameLineup.player_id == Player.player_id
            ).filter(
                GameLineup.game_id == game_id
            ).all()

            result = []
            for lineup, player in lineups:
                lineup_data = {
                    'lineup_id': lineup.lineup_id,
                    'is_starter': lineup.is_starter,
                    'minutes_played': lineup.minutes_played,
                    'game_id': lineup.game_id,
                    'team_id': lineup.team_id,
                    'player_id': lineup.player_id,
                    'player_name': f"{player.first_name} {player.last_name}",
                    'position': player.position,
                    'jersey_number': player.jersey_number
                }
                result.append(lineup_data)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, cls=DatabaseJSONEncoder).encode())

        except Exception as e:
            print(f"Error getting game lineups: {str(e)}")
            self.send_error(500, str(e))
        finally:
            session.close()

    def _handle_get_game_result(self):
        """Handle /game_result/<game_id> endpoint"""
        try:
            game_id = int(self.path.split('/')[-1])
            session = Session()
            
            game = session.get(Game, game_id)
            if not game:
                self.send_error(404, "Game not found")
                return

            home_stats = session.query(PlayerGameStat, Player).join(Player).filter(
                PlayerGameStat.game_id == game_id,
                Player.team_id == game.home_team_id
            ).all()
            
            away_stats = session.query(PlayerGameStat, Player).join(Player).filter(
                PlayerGameStat.game_id == game_id,
                Player.team_id == game.away_team_id
            ).all()
            
            home_team = session.get(Team, game.home_team_id)
            away_team = session.get(Team, game.away_team_id)
            
            result = {
                'game': {
                    'game_id': game.game_id,
                    'home_score': game.home_team_score,
                    'away_score': game.away_team_score,
                    'date': game.game_date,
                    'time': game.game_time,
                    'arena': game.arena,
                    'resimulated': game.resimulated
                },
                'home_team': {
                    'team_id': home_team.team_id,
                    'name': f"{home_team.city} {home_team.team_name}",
                    'players': [{
                        'name': f"{player.first_name} {player.last_name}",
                        'position': player.position,
                        'jersey_number': player.jersey_number,
                        'stats': {
                            'points': stat.points,
                            'rebounds': stat.rebounds,
                            'assists': stat.assists,
                            'steals': stat.steals,
                            'blocks': stat.blocks,
                            'turnovers': stat.turnovers,
                            'fouls': stat.fouls,
                            'fgm': stat.fgm,
                            'fga': stat.fga,
                            'minutes': round(stat.minutes_played, 1)
                        }
                    } for stat, player in home_stats]
                },
                'away_team': {
                    'team_id': away_team.team_id,
                    'name': f"{away_team.city} {away_team.team_name}",
                    'players': [{
                        'name': f"{player.first_name} {player.last_name}",
                        'position': player.position,
                        'jersey_number': player.jersey_number,
                        'stats': {
                            'points': stat.points,
                            'rebounds': stat.rebounds,
                            'assists': stat.assists,
                            'steals': stat.steals,
                            'blocks': stat.blocks,
                            'turnovers': stat.turnovers,
                            'fouls': stat.fouls,
                            'fgm': stat.fgm,
                            'fga': stat.fga,
                            'minutes': round(stat.minutes_played, 1)
                        }
                    } for stat, player in away_stats]
                }
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, cls=DatabaseJSONEncoder).encode())
            
        except Exception as e:
            print(f"Error in _handle_get_game_result: {str(e)}")
            self.send_error(500, str(e))
        finally:
            if 'session' in locals():
                session.close()
    
    def _handle_season_mvp(self):
        """Handle GET request for season MVP data"""
        session = Session()
        try:
            # Get all players with season stats
            players = session.query(Player)\
                .filter(Player.season_games > 0)\
                .all()
            
            # Default MVP data
            mvp_data = {
                'name': "No MVP Yet",
                'ppg': 0.0,
                'rpg': 0.0,
                'apg': 0.0,
                'mvp_score': 0.0,
            }
            
            if players:
                # Calculate MVP score for each player
                mvp_candidates = []
                for player in players:
                    team = session.query(Team).get(player.team_id)
                    win_bonus = 0.1 * (team.season_wins if team else 0)
                    
                    mvp_score = (player.season_ppg * 1.0 + 
                                player.season_rpg * 0.8 + 
                                player.season_apg * 1.2 + 
                                win_bonus)
                    
                    mvp_candidates.append((player, mvp_score))
                
                # Sort by MVP score and get the top player
                if mvp_candidates:
                    mvp_candidates.sort(key=lambda x: x[1], reverse=True)
                    mvp_player, mvp_score = mvp_candidates[0]
                    
                    mvp_data = {
                        'name': f"{mvp_player.first_name} {mvp_player.last_name}",
                        'ppg': player.season_ppg,
                        'rpg': player.season_rpg,
                        'apg': player.season_apg,
                        'mvp_score': mvp_score,
                    }
            
            self.send_response(200)  # Always send 200, even if no MVP yet
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(mvp_data).encode())
            
        except Exception as e:
            print(f"Error getting MVP data: {e}")
            self.send_error(500, str(e))
        finally:
            session.close()

    def _handle_simulate_season(self):
        """Handle POST request to simulate a full season"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        season_data = json.loads(post_data.decode('utf-8'))
        
        favorite_team_id = season_data.get('favorite_team_id')
        
        if not favorite_team_id:
            self.send_error(400, "Favorite team ID is required")
            return
        
        session = Session()
        try:
            # Generate schedule for favorite team
            schedule = generate_favorite_team_schedule(favorite_team_id, games_count=82)
            season_id = datetime.now().year
            
            # Reset stats for favorite team
            favorite_team = session.query(Team).get(favorite_team_id)
            if favorite_team:
                favorite_team.season_wins = 0
                favorite_team.season_losses = 0
                favorite_team.win_rate = 0.0
                favorite_team.avg_points = 0.0
                
                # Reset stats for favorite team's players
                session.query(Player)\
                    .filter_by(team_id=favorite_team_id)\
                    .update({
                        "season_ppg": 0.0,
                        "season_rpg": 0.0,
                        "season_apg": 0.0,
                        "season_games": 0
                    })
                
                session.commit()
            
            results = []
            for home_id, away_id in schedule:
                # Get players for simulation
                home_players = session.query(Player)\
                    .filter_by(team_id=home_id)\
                    .order_by(Player.avg_points.desc())\
                    .limit(8).all()
                    
                away_players = session.query(Player)\
                    .filter_by(team_id=away_id)\
                    .order_by(Player.avg_points.desc())\
                    .limit(8).all()
                
                if len(home_players) >= 5 and len(away_players) >= 5:
                    home_lineup = [p.player_id for p in home_players]
                    away_lineup = [p.player_id for p in away_players]
                    
                    # Apply favorite team boost
                    boost_home = str(home_id) == str(favorite_team_id)
                    boost_away = str(away_id) == str(favorite_team_id)
                    
                    # Get home team arena
                    home_team = session.query(Team).get(home_id)
                    venue = home_team.arena if home_team else "Home Arena"
                    
                    # Simulate game
                    result = simulate_game(
                        home_lineup,
                        away_lineup,
                        arena=venue,
                        is_season_game=True,
                        season_id=season_id,
                        favorite_team_boost=boost_home or boost_away
                    )
                    
                    # Update favorite team's record
                    is_favorite_home = str(home_id) == str(favorite_team_id)
                    favorite_won = (is_favorite_home and result['home_team']['score'] > result['away_team']['score']) or \
                                (not is_favorite_home and result['away_team']['score'] > result['home_team']['score'])
                    
                    if favorite_won:
                        favorite_team.season_wins += 1
                    else:
                        favorite_team.season_losses += 1
                    
                    # Update player stats for favorite team
                    team_key = 'home_team' if is_favorite_home else 'away_team'
                    for player_id, stats in result[team_key]['players'].items():
                        player = session.query(Player).get(int(player_id))
                        if player and str(player.team_id) == str(favorite_team_id):
                            games_played = player.season_games + 1
                            player.season_games = games_played
                            player.season_ppg = ((player.season_ppg * (games_played - 1)) + stats['points']) / games_played
                            player.season_rpg = ((player.season_rpg * (games_played - 1)) + stats['rebounds']) / games_played
                            player.season_apg = ((player.season_apg * (games_played - 1)) + stats['assists']) / games_played
                    
                    session.commit()
                    results.append(result)
            
            # Calculate final win rate for favorite team
            if favorite_team and (favorite_team.season_wins + favorite_team.season_losses) > 0:
                favorite_team.win_rate = favorite_team.season_wins / (favorite_team.season_wins + favorite_team.season_losses)
                session.commit()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
            
        except Exception as e:
            session.rollback()
            print(f"Error simulating season: {e}")
            self.send_error(500, str(e))
        finally:
            session.close()

    def _handle_season_mvp(self):
        """Handle GET request for team's season MVP data"""
        try:
            # Extract team_id from URL
            team_id = int(self.path.split('/')[-1])
            
            session = Session()
            
            # Get the team
            team = session.get(Team, team_id)
            if not team:
                self.send_error(404, "Team not found")
                return
            
            # Get the team's best player
            team_players = session.query(Player)\
                .filter_by(team_id=team_id)\
                .filter(Player.season_games > 0)\
                .all()
                
            mvp_data = {
                'name': "No MVP Yet",
                'ppg': 0.0,
                'rpg': 0.0,
                'apg': 0.0,
                'games_played': 0,
                'team_record': f"{team.season_wins}-{team.season_losses}"
            }
            
            if team_players:
                # Find the best performer
                best_player = max(team_players, 
                    key=lambda p: (p.season_ppg * 1.0 + p.season_rpg * 0.8 + p.season_apg * 1.2))
                
                mvp_data = {
                    'name': f"{best_player.first_name} {best_player.last_name}",
                    'ppg': round(best_player.season_ppg, 1),
                    'rpg': round(best_player.season_rpg, 1),
                    'apg': round(best_player.season_apg, 1),
                    'games_played': best_player.season_games,
                    'team_record': f"{team.season_wins}-{team.season_losses}"
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(mvp_data).encode())
            
        except Exception as e:
            print(f"Error getting team MVP: {e}")
            self.send_error(500, str(e))

    def _handle_team_schedule(self):
        """Handle GET request for team's season schedule"""
        try:
            team_id = int(self.path.split('/')[-1])
            session = Session()
            
            games = session.query(Game)\
                .filter(
                    Game.is_season_game == True,
                    or_(Game.home_team_id == team_id, Game.away_team_id == team_id)
                )\
                .order_by(Game.game_date, Game.game_time)\
                .all()
            
            schedule = []
            for game in games:
                home_team = session.query(Team).get(game.home_team_id)
                away_team = session.query(Team).get(game.away_team_id)
                
                schedule.append({
                    'date': game.game_date.isoformat(),
                    'home_team_id': game.home_team_id,
                    'away_team_id': game.away_team_id,
                    'home_team': f"{home_team.city} {home_team.team_name}",
                    'away_team': f"{away_team.city} {away_team.team_name}",
                    'home_score': game.home_team_score,
                    'away_score': game.away_team_score,
                    'arena': game.arena
                })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(schedule).encode())
            
        except Exception as e:
            print(f"Error getting team schedule: {e}")
            self.send_error(500, str(e))
        finally:
            session.close()

    def _handle_team_info(self):
        """Handle GET request for team information"""
        try:
            team_id = int(self.path.split('/')[-1])
            session = Session()
            
            team = session.get(Team, team_id)
            if not team:
                self.send_error(404, "Team not found")
                return
            
            team_data = {
                'name': f"{team.city} {team.team_name}",
                'season_wins': team.season_wins,
                'season_losses': team.season_losses,
                'win_rate': team.win_rate if team.win_rate else 0.0,
                'avg_points': team.avg_points if team.avg_points else 0.0
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(team_data).encode())
            
        except Exception as e:
            print(f"Error getting team info: {e}")
            self.send_error(500, str(e))

    def _serve_file(self, filename):
        """Serve static files"""
        file_path = filename
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                self.send_response(200)
                if file_path.endswith('.html'):
                    self.send_header('Content-type', 'text/html')
                elif file_path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif file_path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                self.end_headers()
                self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, f"File {filename} not found")

    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_DELETE(self):
        """Handle DELETE requests"""
        if self.path.startswith('/delete_game/'):
            try:
                game_id = int(self.path.split('/')[-1])
                session = Session()
                
                # Delete associated records first
                session.query(PlayerGameStat).filter_by(game_id=game_id).delete()
                session.query(GameLineup).filter_by(game_id=game_id).delete()
                session.query(Game).filter_by(game_id=game_id).delete()
                
                session.commit()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
            except Exception as e:
                print(f"Error deleting game: {str(e)}")
                self.send_error(500, str(e))
            finally:
                session.close()
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/simulate_game':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            game_data = json.loads(post_data.decode('utf-8'))
            
            try:
                # Validate input data
                if not game_data.get('home_players') or not game_data.get('away_players'):
                    raise ValueError("Missing player selections")
                
                if len(game_data['home_players']) < 5 or len(game_data['away_players']) < 5:
                    raise ValueError("Need at least 5 players per team")
                
                session = Session()
                try:
                    # If resimulating, clear old stats and lineups
                    resimulate_id = game_data.get('resimulate_id')
                    if resimulate_id:
                        # Verify game exists
                        game = session.query(Game).get(resimulate_id)
                        if not game:
                            raise ValueError(f"Game {resimulate_id} not found")
                        
                        # Delete old stats and lineups
                        session.query(PlayerGameStat).filter_by(game_id=resimulate_id).delete()
                        session.query(GameLineup).filter_by(game_id=resimulate_id).delete()
                        session.commit()
                    
                    # Get home team arena for the venue
                    home_team = session.query(Team).join(Player).filter(
                        Player.player_id == game_data['home_players'][0]
                    ).first()
                    
                    venue = home_team.arena if home_team else "Home Arena"
                    
                    # Simulate game with selected players
                    result = simulate_game(
                        game_data['home_players'],
                        game_data['away_players'],
                        arena=venue,
                        resimulate_id=resimulate_id
                    )
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result, cls=DatabaseJSONEncoder).encode())
                
                finally:
                    session.close()
                    
            except Exception as e:
                print(f"Error simulating game: {str(e)}")
                self.send_error(500, str(e))
        elif self.path == '/simulate_season':
            self._handle_simulate_season()
        else:
            self.send_error(404)

    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, RequestHandler)
    print('Server running on port 8000...')
    print('Access the application at http://localhost:8000')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
