import pandas as pd
import requests
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize YouTube API with your API key
API_KEY = os.getenv('YOUTUBE_API_KEY')
if not API_KEY:
    API_KEY = input("Enter your YouTube API key: ")
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Spotify client credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    SPOTIFY_CLIENT_ID = input("Enter your Spotify Client ID: ")
    SPOTIFY_CLIENT_SECRET = input("Enter your Spotify Client Secret: ")
spotify_token = None  # Initialize token as None


# Function to get Spotify access token
def get_spotify_access_token():
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {os.getenv('SPOTIFY_CLIENT_CREDS')}"
    }
    data = {"grant_type": "client_credentials"}
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        print(f"Failed to obtain Spotify token: {e}")
        return None


# Function to get the song name from Spotify API
def get_spotify_song_name(spotify_link):
    global spotify_token
    if spotify_token is None:
        spotify_token = get_spotify_access_token()  # Get a token if not already set

    track_id = spotify_link.split('/')[-1].split('?')[0]
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    
    # Attempt API call and handle token expiry
    headers = {"Authorization": f"Bearer {spotify_token}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    
        # If token has expired, get a new one and retry
        if response.status_code == 401:  # Unauthorized error, likely due to token expiry
            print("Spotify token expired. Refreshing token...")
            spotify_token = get_spotify_access_token()
            if spotify_token:
                headers["Authorization"] = f"Bearer {spotify_token}"
                response = requests.get(url, headers=headers)  # Retry with new token
                response.raise_for_status()  # Raise an HTTPError for bad responses
            else:
                print("Failed to refresh Spotify token.")
                return None
    
        track_info = response.json()
        print(f"Found song: {track_info['name']} by {track_info['artists'][0]['name']}")
        return track_info['name'], track_info['artists'][0]['name']
    except requests.exceptions.RequestException as e:
        print(f"Spotify API error for link: {spotify_link}, error: {e}")
        return None

# Function to search for a YouTube link by song name
def search_youtube(song_name):
    if song_name is None:
        print("No song name provided for YouTube search.")
        return None
    print(f"Searching YouTube for song: {song_name}")
    request = youtube.search().list(
        part="snippet",
        q=song_name,
        type="video",
        maxResults=1
    )
    try:
        response = request.execute()
        print(f"YouTube search response: {response}")
        
        # Get the video ID of the first result
        if response['items']:
            video_id = response['items'][0]['id']['videoId']
            youtube_link = f"https://www.youtube.com/watch?v={video_id}"
            print(f"Found YouTube link: {youtube_link}")
            return youtube_link
        else:
            print("No YouTube video found for the song.")
    except Exception as e:
        print(f"Error accessing YouTube API for song: {song_name}, error: {e}")
    return None

# Load the Excel file with Spotify links
file_path = input("Enter the path to your Excel file with Spotify links: ")
df = pd.read_excel(file_path)

# Add a new column for YouTube links
df['YouTube Link'] = ''

# Iterate through each row and get the corresponding YouTube link
for index, row in df.iterrows():
    spotify_link = row.iloc[0]  # Assuming the Spotify link is in the first column
    song_name, artist_name = get_spotify_song_name(spotify_link)  # Get the song name and artist using Spotify API
    search_query = f"{song_name} {artist_name}"  # Combine song name and artist for a more accurate search
    # Search YouTube and add the link to the DataFrame
    youtube_link = search_youtube(search_query)
    df.at[index, 'YouTube Link'] = youtube_link

# Save the DataFrame with YouTube links to a new Excel file
output_file_path = 'youtube.xlsx'  # Adjust your output file path if needed
df.to_excel(output_file_path, index=False)

print("YouTube links added and saved successfully!")
