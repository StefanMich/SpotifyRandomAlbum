#!/usr/bin/env python3

import spotipy
from spotipy.oauth2 import SpotifyOAuth

scope = 'user-library-read user-read-playback-state user-modify-playback-state user-follow-read'
spotify = spotipy.Spotify(client_credentials_manager=SpotifyOAuth(scope=scope))
