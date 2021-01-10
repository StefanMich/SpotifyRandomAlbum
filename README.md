# Spotify Random Album 

Script that queues random albums to your spotify queue. 
Supports queueing random albums from your followed artists, or from a specified
playlist.

# Setup
- Go to https://developer.spotify.com/dashboard/applications and create an app.
- Go to 'Edit Settings' and add a redirect URI. It does not have to be a working
URI, but you need to specify the same in the environment variable (next step). 
Example 'http://127.0.0.1:8001 '
- Set the following enironment variables 
    - SPOTIPY_CLIENT_ID (from your spotify app)
    - SPOTIPY_CLIENT_SECRET (from your spotify app)
    - SPOTIPY_REDIRECT_URI (has to be the same as in the previous step)
- Create a virtual environment 
- Run pip3 install pip-tools 
- Run pipsync requirements.txt

# Usage
`python3 main.py`
