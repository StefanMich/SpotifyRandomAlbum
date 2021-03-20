# Spotify Random Album 

Script that queues random albums to your spotify queue. 
Supports queueing random albums from your followed artists, or from a specified
playlist.

# Setup
- Go to https://developer.spotify.com/dashboard/applications and create an app.
- Go to 'Edit Settings' and add a redirect URI. It does not have to be a working
URI, but you need to specify the same in the environment variable (next step). 
Example 'http://127.0.0.1:8001 '
- Copy .env.template to a .env file and set the values as follows: 
    - SPOTIPY_CLIENT_ID - the client id from your spotify app
    - SPOTIPY_CLIENT_SECRET - the client secret from your spotify app
    - SPOTIPY_REDIRECT_URI - the redirect uri used in the previous step
- `pip install pipenv`
- `pipenv shell`

# Usage
`pipenv run python main.py`
