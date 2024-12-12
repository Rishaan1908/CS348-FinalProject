# database_setup.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Time, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# Create database engine
engine = create_engine('sqlite:///nba_simulator.db', echo=True)
Base = declarative_base()

# Define models

class Team(Base):
    __tablename__ = 'teams'
    
    team_id = Column(Integer, primary_key=True)
    team_name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    conference = Column(String, nullable=False)
    division = Column(String, nullable=False)
    win_rate = Column(Float, default=0.0)
    avg_points = Column(Float, default=0.0)
    season_wins = Column(Integer, default=0)  # For season tracking
    season_losses = Column(Integer, default=0)  # For season tracking
    playoff_seed = Column(Integer)  # For playoff seeding
    arena = Column(String, nullable=False)
    
    players = relationship("Player", back_populates="team")
    home_games = relationship("Game", foreign_keys="Game.home_team_id", backref="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", backref="away_team")

class Player(Base):
    __tablename__ = 'players'
    
    player_id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    position = Column(String)
    height = Column(Float)
    weight = Column(Float)
    jersey_number = Column(Integer)
    team_id = Column(Integer, ForeignKey('teams.team_id'))
    avg_points = Column(Float)
    avg_rebounds = Column(Float)
    avg_assists = Column(Float)
    avg_steals = Column(Float)
    avg_blocks = Column(Float)
    avg_turnovers = Column(Float)
    avg_fouls = Column(Float)
    fg_percentage = Column(Float)
    mvp_count = Column(Integer, default=0)  
    season_ppg = Column(Float, default=0.0) 
    season_rpg = Column(Float, default=0.0)
    season_apg = Column(Float, default=0.0)
    season_games = Column(Integer, default=0)
    
    team = relationship("Team", back_populates="players")
    game_lineups = relationship("GameLineup", backref="player")
    game_stats = relationship("PlayerGameStat", backref="player")

class Game(Base):
    __tablename__ = 'games'
    
    game_id = Column(Integer, primary_key=True)
    game_date = Column(Date, nullable=False)
    game_time = Column(Time, nullable=False)
    resimulated = Column(Boolean, default=False)
    home_team_score = Column(Integer)
    away_team_score = Column(Integer)
    arena = Column(String)
    home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    away_team_id = Column(Integer, ForeignKey('teams.team_id'))
    is_season_game = Column(Boolean, default=False)  
    season_id = Column(Integer, nullable=True)  
    
    lineups = relationship("GameLineup", backref="game")
    player_stats = relationship("PlayerGameStat", backref="game")

class GameLineup(Base):
    __tablename__ = 'game_lineups'
    
    lineup_id = Column(Integer, primary_key=True)
    is_starter = Column(Boolean, nullable=False)
    minutes_played = Column(Float, nullable=False)
    game_id = Column(Integer, ForeignKey('games.game_id'))
    team_id = Column(Integer, ForeignKey('teams.team_id'))
    player_id = Column(Integer, ForeignKey('players.player_id'))

class PlayerGameStat(Base):
    __tablename__ = 'player_game_stats'
    
    stat_id = Column(Integer, primary_key=True)
    points = Column(Integer)
    rebounds = Column(Integer)
    assists = Column(Integer)
    steals = Column(Integer)
    blocks = Column(Integer)
    turnovers = Column(Integer)
    fouls = Column(Integer)
    fgm = Column(Integer)
    fga = Column(Integer)
    minutes_played = Column(Float)
    game_id = Column(Integer, ForeignKey('games.game_id'))
    player_id = Column(Integer, ForeignKey('players.player_id'))

# Create all tables
Base.metadata.create_all(engine)

# Create session factory
Session = sessionmaker(bind=engine)

def populate_teams():
    session = Session()
    
    # NBA teams data
    teams_data = [
        {"team_name": "Hawks", "city": "Atlanta", "conference": "Eastern", "division": "Southeast", "win_rate": 0.0, "arena": "State Farm Arena"},
        {"team_name": "Celtics", "city": "Boston", "conference": "Eastern", "division": "Atlantic", "win_rate": 0.0, "arena": "TD Garden"},
        {"team_name": "Nets", "city": "Brooklyn", "conference": "Eastern", "division": "Atlantic", "win_rate": 0.0, "arena": "Barclays Center"},
        {"team_name": "Hornets", "city": "Charlotte", "conference": "Eastern", "division": "Southeast", "win_rate": 0.0, "arena": "Spectrum Center"},
        {"team_name": "Bulls", "city": "Chicago", "conference": "Eastern", "division": "Central", "win_rate": 0.0, "arena": "United Center"},
        {"team_name": "Cavaliers", "city": "Cleveland", "conference": "Eastern", "division": "Central", "win_rate": 0.0, "arena": "Rocket Mortgage FieldHouse"},
        {"team_name": "Mavericks", "city": "Dallas", "conference": "Western", "division": "Southwest", "win_rate": 0.0, "arena": "American Airlines Center"},
        {"team_name": "Nuggets", "city": "Denver", "conference": "Western", "division": "Northwest", "win_rate": 0.0, "arena": "Ball Arena"},
        {"team_name": "Pistons", "city": "Detroit", "conference": "Eastern", "division": "Central", "win_rate": 0.0, "arena": "Little Caesars Arena"},
        {"team_name": "Warriors", "city": "Golden State", "conference": "Western", "division": "Pacific", "win_rate": 0.0, "arena": "Chase Center"},
        {"team_name": "Rockets", "city": "Houston", "conference": "Western", "division": "Southwest", "win_rate": 0.0, "arena": "Toyota Center"},
        {"team_name": "Pacers", "city": "Indiana", "conference": "Eastern", "division": "Central", "win_rate": 0.0, "arena": "Gainbridge Fieldhouse"},
        {"team_name": "Clippers", "city": "Los Angeles", "conference": "Western", "division": "Pacific", "win_rate": 0.0, "arena": "Crypto.com Arena"},
        {"team_name": "Lakers", "city": "Los Angeles", "conference": "Western", "division": "Pacific", "win_rate": 0.0, "arena": "Crypto.com Arena"},
        {"team_name": "Grizzlies", "city": "Memphis", "conference": "Western", "division": "Southwest", "win_rate": 0.0, "arena": "FedExForum"},
        {"team_name": "Heat", "city": "Miami", "conference": "Eastern", "division": "Southeast", "win_rate": 0.0, "arena": "Kaseya Center"},
        {"team_name": "Bucks", "city": "Milwaukee", "conference": "Eastern", "division": "Central", "win_rate": 0.0, "arena": "Fiserv Forum"},
        {"team_name": "Timberwolves", "city": "Minnesota", "conference": "Western", "division": "Northwest", "win_rate": 0.0, "arena": "Target Center"},
        {"team_name": "Pelicans", "city": "New Orleans", "conference": "Western", "division": "Southwest", "win_rate": 0.0, "arena": "Smoothie King Center"},
        {"team_name": "Knicks", "city": "New York", "conference": "Eastern", "division": "Atlantic", "win_rate": 0.0, "arena": "Madison Square Garden"},
        {"team_name": "Thunder", "city": "Oklahoma City", "conference": "Western", "division": "Northwest", "win_rate": 0.0, "arena": "Paycom Center"},
        {"team_name": "Magic", "city": "Orlando", "conference": "Eastern", "division": "Southeast", "win_rate": 0.0, "arena": "Amway Center"},
        {"team_name": "76ers", "city": "Philadelphia", "conference": "Eastern", "division": "Atlantic", "win_rate": 0.0, "arena": "Wells Fargo Center"},
        {"team_name": "Suns", "city": "Phoenix", "conference": "Western", "division": "Pacific", "win_rate": 0.0, "arena": "Footprint Center"},
        {"team_name": "Trail Blazers", "city": "Portland", "conference": "Western", "division": "Northwest", "win_rate": 0.0, "arena": "Moda Center"},
        {"team_name": "Kings", "city": "Sacramento", "conference": "Western", "division": "Pacific", "win_rate": 0.0, "arena": "Golden 1 Center"},
        {"team_name": "Spurs", "city": "San Antonio", "conference": "Western", "division": "Southwest", "win_rate": 0.0, "arena": "Frost Bank Center"},
        {"team_name": "Raptors", "city": "Toronto", "conference": "Eastern", "division": "Atlantic", "win_rate": 0.0, "arena": "Scotiabank Arena"},
        {"team_name": "Jazz", "city": "Utah", "conference": "Western", "division": "Northwest", "win_rate": 0.0, "arena": "Delta Center"},
        {"team_name": "Wizards", "city": "Washington", "conference": "Eastern", "division": "Southeast", "win_rate": 0.0, "arena": "Capital One Arena"}
    ]
    
    for team_data in teams_data:
        team = Team(**team_data)
        session.add(team)
    
    try:
        session.commit()
        print("Teams data populated successfully!")
    except Exception as e:
        print(f"Error populating teams: {e}")
        session.rollback()
    finally:
        session.close()

def get_all_teams():
    session = Session()
    teams = session.query(Team).all()
    session.close()
    return teams

if __name__ == "__main__":
    populate_teams()