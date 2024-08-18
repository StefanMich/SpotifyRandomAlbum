#!/usr/bin/env python3

import spotipy
from spotipy import DjangoSessionCacheHandler
from spotipy.oauth2 import SpotifyOAuth

scope = 'user-library-read user-read-playback-state user-modify-playback-state user-follow-read'


def get_token(request):
    cache_handler = DjangoSessionCacheHandler(request)
    auth = SpotifyOAuth(scope=scope, cache_handler=cache_handler, show_dialog=True)
    token = auth.get_cached_token()
    if not token:
        raise AttributeError(auth.get_authorize_url())
    else:
        return token['access_token']

def token_callback(request):
    sp_oauth = SpotifyOAuth(
        scope=scope, cache_handler=DjangoSessionCacheHandler(request))
    code = sp_oauth.parse_response_code(request.GET['code'])
    token_info = sp_oauth.get_access_token(code)
    if token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])


def spotify(request) -> spotipy.Spotify:
    token = get_token(request)
    client = spotipy.Spotify(auth=token)
    return client

def logout(request):
    cache_handler = DjangoSessionCacheHandler(request)
    cache_handler.save_token_to_cache('INVALID')
