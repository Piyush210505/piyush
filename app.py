import os
import json
import random
import base64
from datetime import datetime
from urllib.parse import urlencode
import openai
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Spotify Configuration
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
# Use Replit environment domain or fallback to localhost
REPLIT_DOMAIN = os.getenv("REPLIT_DOMAIN")
if REPLIT_DOMAIN:
    SPOTIFY_REDIRECT_URI = f"https://{REPLIT_DOMAIN}/callback"
else:
    SPOTIFY_REDIRECT_URI = "http://localhost:3000/callback"

SCOPE = "user-read-private user-read-email playlist-modify-private playlist-modify-public"

# Cache to store generated playlists
playlist_cache = {}

# Function to generate a playlist using OpenAI
def generate_playlist_with_openai(emotion):
    try:
        if not OPENAI_API_KEY:
            return None
        
        # Use GPT-4o for the latest model
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a music expert who creates personalized playlists based on emotions."},
                {"role": "user", "content": f"Create a playlist of 10 songs that match the emotion '{emotion}'. For each song, provide title, artist, and an approximate duration in format mm:ss (like '3:45'). Also give the playlist a creative title. Return the result in JSON format with fields 'title' for the playlist name and 'songs' array with objects containing 'title', 'artist', and 'duration' for each song."}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Add placeholder album covers
        for song in result.get("songs", []):
            song["albumCover"] = f"https://picsum.photos/seed/{song['title'].replace(' ', '')}{song['artist'].replace(' ', '')}/300/300"
        
        return result
    except Exception as e:
        print(f"Error generating playlist with OpenAI: {e}")
        return None

# Fallback function to generate a playlist when OpenAI is not available
def generate_fallback_playlist(emotion):
    emotions_map = {
        "happy": {
            "title": "Upbeat Happiness Mix",
            "songs": [
                {"title": "Happy", "artist": "Pharrell Williams", "duration": "3:53", "albumCover": "https://picsum.photos/seed/Happy1/300/300"},
                {"title": "Can't Stop the Feeling!", "artist": "Justin Timberlake", "duration": "3:56", "albumCover": "https://picsum.photos/seed/CantStopTheFeeling/300/300"},
                {"title": "Good as Hell", "artist": "Lizzo", "duration": "2:39", "albumCover": "https://picsum.photos/seed/GoodAsHell/300/300"},
                {"title": "Walking on Sunshine", "artist": "Katrina & The Waves", "duration": "3:54", "albumCover": "https://picsum.photos/seed/WalkingOnSunshine/300/300"},
                {"title": "Uptown Funk", "artist": "Mark Ronson ft. Bruno Mars", "duration": "4:30", "albumCover": "https://picsum.photos/seed/UptownFunk/300/300"},
                {"title": "I Gotta Feeling", "artist": "Black Eyed Peas", "duration": "4:49", "albumCover": "https://picsum.photos/seed/IGottaFeeling/300/300"},
                {"title": "Shut Up and Dance", "artist": "WALK THE MOON", "duration": "3:17", "albumCover": "https://picsum.photos/seed/ShutUpAndDance/300/300"},
                {"title": "Best Day of My Life", "artist": "American Authors", "duration": "3:14", "albumCover": "https://picsum.photos/seed/BestDayOfMyLife/300/300"},
                {"title": "On Top of the World", "artist": "Imagine Dragons", "duration": "3:12", "albumCover": "https://picsum.photos/seed/OnTopOfTheWorld/300/300"},
                {"title": "Shake It Off", "artist": "Taylor Swift", "duration": "3:39", "albumCover": "https://picsum.photos/seed/ShakeItOff/300/300"},
            ]
        },
        "sad": {
            "title": "Melancholy Moments",
            "songs": [
                {"title": "Someone Like You", "artist": "Adele", "duration": "4:45", "albumCover": "https://picsum.photos/seed/SomeoneLikeYou/300/300"},
                {"title": "Fix You", "artist": "Coldplay", "duration": "4:55", "albumCover": "https://picsum.photos/seed/FixYou/300/300"},
                {"title": "All I Want", "artist": "Kodaline", "duration": "5:05", "albumCover": "https://picsum.photos/seed/AllIWant/300/300"},
                {"title": "Skinny Love", "artist": "Bon Iver", "duration": "3:58", "albumCover": "https://picsum.photos/seed/SkinnyLove/300/300"},
                {"title": "Hurt", "artist": "Johnny Cash", "duration": "3:38", "albumCover": "https://picsum.photos/seed/Hurt/300/300"},
                {"title": "How to Save a Life", "artist": "The Fray", "duration": "4:22", "albumCover": "https://picsum.photos/seed/HowToSaveALife/300/300"},
                {"title": "The Night We Met", "artist": "Lord Huron", "duration": "3:28", "albumCover": "https://picsum.photos/seed/TheNightWeMet/300/300"},
                {"title": "Tears in Heaven", "artist": "Eric Clapton", "duration": "4:36", "albumCover": "https://picsum.photos/seed/TearsInHeaven/300/300"},
                {"title": "Everybody Hurts", "artist": "R.E.M.", "duration": "5:17", "albumCover": "https://picsum.photos/seed/EverybodyHurts/300/300"},
                {"title": "Nothing Compares 2 U", "artist": "Sinéad O'Connor", "duration": "5:07", "albumCover": "https://picsum.photos/seed/NothingCompares2U/300/300"},
            ]
        },
        "energetic": {
            "title": "High Energy Mix",
            "songs": [
                {"title": "Don't Stop Me Now", "artist": "Queen", "duration": "3:29", "albumCover": "https://picsum.photos/seed/DontStopMeNow/300/300"},
                {"title": "Eye of the Tiger", "artist": "Survivor", "duration": "4:05", "albumCover": "https://picsum.photos/seed/EyeOfTheTiger/300/300"},
                {"title": "Stronger", "artist": "Kanye West", "duration": "5:12", "albumCover": "https://picsum.photos/seed/Stronger/300/300"},
                {"title": "Titanium", "artist": "David Guetta ft. Sia", "duration": "4:05", "albumCover": "https://picsum.photos/seed/Titanium/300/300"},
                {"title": "All I Do Is Win", "artist": "DJ Khaled", "duration": "3:51", "albumCover": "https://picsum.photos/seed/AllIDoIsWin/300/300"},
                {"title": "Power", "artist": "Kanye West", "duration": "4:52", "albumCover": "https://picsum.photos/seed/Power/300/300"},
                {"title": "Till I Collapse", "artist": "Eminem", "duration": "4:57", "albumCover": "https://picsum.photos/seed/TillICollapse/300/300"},
                {"title": "Lose Yourself", "artist": "Eminem", "duration": "5:26", "albumCover": "https://picsum.photos/seed/LoseYourself/300/300"},
                {"title": "Remember the Name", "artist": "Fort Minor", "duration": "3:50", "albumCover": "https://picsum.photos/seed/RememberTheName/300/300"},
                {"title": "Can't Hold Us", "artist": "Macklemore & Ryan Lewis", "duration": "4:18", "albumCover": "https://picsum.photos/seed/CantHoldUs/300/300"},
            ]
        },
        "relaxed": {
            "title": "Calm & Cozy Playlist",
            "songs": [
                {"title": "Weightless", "artist": "Marconi Union", "duration": "8:08", "albumCover": "https://picsum.photos/seed/Weightless/300/300"},
                {"title": "Claire de Lune", "artist": "Claude Debussy", "duration": "5:01", "albumCover": "https://picsum.photos/seed/ClaireDeLune/300/300"},
                {"title": "Everything's Not Lost", "artist": "Coldplay", "duration": "5:09", "albumCover": "https://picsum.photos/seed/EverythingsNotLost/300/300"},
                {"title": "Banana Pancakes", "artist": "Jack Johnson", "duration": "3:11", "albumCover": "https://picsum.photos/seed/BananaPancakes/300/300"},
                {"title": "Dreams", "artist": "Fleetwood Mac", "duration": "4:14", "albumCover": "https://picsum.photos/seed/Dreams/300/300"},
                {"title": "Easy", "artist": "Commodores", "duration": "4:16", "albumCover": "https://picsum.photos/seed/Easy/300/300"},
                {"title": "Bloom", "artist": "The Paper Kites", "duration": "3:27", "albumCover": "https://picsum.photos/seed/Bloom/300/300"},
                {"title": "Holocene", "artist": "Bon Iver", "duration": "5:37", "albumCover": "https://picsum.photos/seed/Holocene/300/300"},
                {"title": "Yellow", "artist": "Coldplay", "duration": "4:27", "albumCover": "https://picsum.photos/seed/Yellow/300/300"},
                {"title": "Heartbeats", "artist": "José González", "duration": "2:41", "albumCover": "https://picsum.photos/seed/Heartbeats/300/300"},
            ]
        }
    }

    # Return the playlist for the given emotion, or a default one if not found
    return emotions_map.get(emotion.lower(), {
        "title": f"Custom {emotion.capitalize()} Mix",
        "songs": [
            {"title": f"Song about {emotion} 1", "artist": "Artist 1", "duration": "3:30", "albumCover": "https://picsum.photos/seed/Song1/300/300"},
            {"title": f"Song about {emotion} 2", "artist": "Artist 2", "duration": "3:45", "albumCover": "https://picsum.photos/seed/Song2/300/300"},
            {"title": f"Song about {emotion} 3", "artist": "Artist 3", "duration": "4:15", "albumCover": "https://picsum.photos/seed/Song3/300/300"},
            {"title": f"Song about {emotion} 4", "artist": "Artist 4", "duration": "3:22", "albumCover": "https://picsum.photos/seed/Song4/300/300"},
            {"title": f"Song about {emotion} 5", "artist": "Artist 5", "duration": "3:51", "albumCover": "https://picsum.photos/seed/Song5/300/300"},
            {"title": f"Song about {emotion} 6", "artist": "Artist 6", "duration": "4:02", "albumCover": "https://picsum.photos/seed/Song6/300/300"},
            {"title": f"Song about {emotion} 7", "artist": "Artist 7", "duration": "3:18", "albumCover": "https://picsum.photos/seed/Song7/300/300"},
            {"title": f"Song about {emotion} 8", "artist": "Artist 8", "duration": "4:35", "albumCover": "https://picsum.photos/seed/Song8/300/300"},
            {"title": f"Song about {emotion} 9", "artist": "Artist 9", "duration": "3:47", "albumCover": "https://picsum.photos/seed/Song9/300/300"},
            {"title": f"Song about {emotion} 10", "artist": "Artist 10", "duration": "3:33", "albumCover": "https://picsum.photos/seed/Song10/300/300"},
        ]
    })

# Function to create a Spotify client
def get_spotify_client():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    
    try:
        cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SCOPE,
            cache_handler=cache_handler
        )
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        print(f"Error creating Spotify client: {e}")
        return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_playlist', methods=['POST'])
def generate_playlist():
    if request.method == 'POST':
        emotion = request.form.get('emotion', '').strip()
        if not emotion:
            return jsonify({'error': 'Emotion is required'}), 400
        
        # Check if we already have this playlist cached
        if emotion in playlist_cache:
            return jsonify(playlist_cache[emotion])
        
        # Try to generate with OpenAI first
        playlist = generate_playlist_with_openai(emotion)
        
        # If OpenAI generation fails, use fallback
        if not playlist:
            playlist = generate_fallback_playlist(emotion)
        
        # Cache the result
        playlist_cache[emotion] = playlist
        
        return jsonify(playlist)

@app.route('/spotify_login')
def spotify_login():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return jsonify({'error': 'Spotify API credentials are not configured'}), 500
    
    spotify = get_spotify_client()
    if not spotify:
        return jsonify({'error': 'Failed to initialize Spotify client'}), 500
    
    auth_url = spotify.auth_manager.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def spotify_callback():
    spotify = get_spotify_client()
    if not spotify:
        return redirect(url_for('index'))
    
    code = request.args.get('code')
    if code:
        spotify.auth_manager.get_access_token(code)
        return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/create_spotify_playlist', methods=['POST'])
def create_spotify_playlist():
    spotify = get_spotify_client()
    if not spotify:
        return jsonify({'error': 'Not authenticated with Spotify'}), 401
    
    try:
        data = request.json
        if not data or 'playlist' not in data:
            return jsonify({'error': 'No playlist data provided'}), 400
        
        playlist_data = data['playlist']
        playlist_title = playlist_data.get('title', 'My Generated Playlist')
        songs = playlist_data.get('songs', [])
        
        # Create a new playlist
        user_info = spotify.current_user()
        user_id = user_info['id']
        
        created_playlist = spotify.user_playlist_create(
            user=user_id,
            name=playlist_title,
            public=False,
            description=f"Playlist generated based on emotion"
        )
        
        # Search for each song and add to playlist
        track_uris = []
        for song in songs:
            try:
                query = f"track:{song['title']} artist:{song['artist']}"
                result = spotify.search(q=query, type='track', limit=1)
                
                if result['tracks']['items']:
                    track_uris.append(result['tracks']['items'][0]['uri'])
            except Exception as e:
                print(f"Error searching for track {song['title']}: {e}")
        
        # Add tracks to the playlist
        if track_uris:
            spotify.playlist_add_items(created_playlist['id'], track_uris)
        
        return jsonify({
            'success': True,
            'playlist_url': created_playlist['external_urls']['spotify']
        })
    
    except Exception as e:
        print(f"Error creating Spotify playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/current_user')
def get_current_user():
    spotify = get_spotify_client()
    if not spotify:
        return jsonify({'authenticated': False})
    
    try:
        user_info = spotify.current_user()
        return jsonify({
            'authenticated': True,
            'name': user_info.get('display_name', 'Spotify User'),
            'email': user_info.get('email'),
            'id': user_info.get('id')
        })
    except:
        return jsonify({'authenticated': False})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Use 0.0.0.0 to make the app accessible externally
    port = int(os.getenv('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)