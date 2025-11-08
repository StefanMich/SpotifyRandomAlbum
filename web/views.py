from dataclasses import dataclass
from enum import Enum
import logging
import random
from concurrent.futures import ThreadPoolExecutor

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.templatetags.static import static
from django.views.decorators.http import require_http_methods

from exception_parser import SpotifyException
from spotify_logic.album import (
    get_album,
    get_random_artist_album_list,
    get_saved_albums,
    queue_tracks,
)
from spotify_logic.client import (
    spotify,
    get_token,
    token_callback,
    logout as client_logout,
)
from spotify_logic.playlist import (
    followed_playlists,
    get_random_album_from_playlist,
)
from spotify_logic.lastfm import get_album_playcount

logger = logging.getLogger(__name__)

def get_cover_art_url(album):
    try:
        url = album['images'][0]['url']
    except IndexError:
        url = static('/web/no_cover_art.jpg')
    return url

class Album:
    def __init__(self, item_json, lastfm_username: str = None):
        # item_json can be an album object or a playlist track object which contains a track object
        is_track_object = 'track' in item_json and item_json['track'] is not None

        if is_track_object:
            track_data = item_json['track']
            album_data = track_data.get('album', {})
            self.title = album_data.get('name', 'Unknown Album')
            self.id = album_data.get('id')
            artists = track_data.get('artists', [])
            self.artist = artists[0]['name'] if artists else 'Unknown Artist'
        else:  # it's an album object
            self.title = item_json.get('name', 'Unknown Album')
            self.id = item_json.get('id')
            artists = item_json.get('artists', [])
            self.artist = artists[0]['name'] if artists else 'Unknown Artist'

        self.album_art_url = get_cover_art_url(item_json)
        self.playcount = get_album_playcount(self.artist, self.title, lastfm_username)

def get_lastfm_username(request) -> str:
    return request.COOKIES.get('lastfm_username', '')


@require_http_methods(['GET'])
def display_albums(request):
    try:
        client = spotify(request)
    except AttributeError as e:
        return HttpResponseRedirect(e.args[0])
    lastfm_username = get_lastfm_username(request)
    artist_name, other_albums, spotlight_album = prepare_albums(client, lastfm_username)

    return render(request, 'display_albums.html', {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
        'mode': 'album',
    })


def prepare_albums(client, lastfm_username: str = None, unused=None):
    artist, albums = get_random_artist_album_list(client)
    if not albums:
        logger.debug(f'No albums found for artist: {artist["name"]} {artist["id"]}')
        return prepare_albums(client, lastfm_username)
    logger.debug(f'Preparing artist: {artist["name"]} {artist["id"]}')
    saved = get_saved_albums(client, albums)
    weights = [3 if is_saved else 1 for is_saved in saved]


    with ThreadPoolExecutor() as executor:
        view_albums = list(executor.map(
            lambda item: Album(item, lastfm_username), albums))

    spotlight_album = random.choices(view_albums, weights=weights)[0]
    other_albums = [album for album in view_albums if album.id != spotlight_album.id]
    artist_name = artist['name']
    return artist_name, other_albums, spotlight_album


@require_http_methods(['GET', 'POST'])
def display_from_playlist(request, playlist_id):
    client = spotify(request)
    lastfm_username = get_lastfm_username(request)
    artist_name, other_albums, spotlight_album = prepare_from_playlist(
        client, playlist_id, lastfm_username)

    if request.htmx:
        template = 'album_rotator.html'
    else:
        template = 'display_albums.html'

    return render(request, template, {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
        'mode': 'playlist',
        'playlist_id': playlist_id,
    })


def prepare_from_playlist(client, playlist_id, lastfm_username: str = None):
    artist_name, album, other = get_random_album_from_playlist(client, playlist_id)
    return (artist_name,
            [Album(item, lastfm_username) for item in other],
            Album(album, lastfm_username))


class Mode(Enum):
    ALBUM = 'album', prepare_albums
    PLAYLIST = 'playlist', prepare_from_playlist

    def __new__(cls, identifier, func):
        obj = object.__new__(cls)
        obj._value_ = identifier
        obj.func = func
        return obj

    def __init__(self, identifier, func):
        self.identifier = self.name
        self.func = func


@require_http_methods(['POST'])
def queue_album(request, album_id):
    client = spotify(request)
    mode = request.POST.get('mode')
    playlist_id = request.POST.get('playlist_id', None)
    album = get_album(client, album_id)
    error = None
    try:
        queue_tracks(client, album)
    except SpotifyException as e:
        error = e.args[0]
    lastfm_username = get_lastfm_username(request)
    mode_func = Mode(mode).func

    if mode == 'album':
        artist_name, other_albums, spotlight_album = mode_func(
            client, lastfm_username, None)
    else:
        artist_name, other_albums, spotlight_album = mode_func(
            client, playlist_id, lastfm_username)

    return render(request, 'album_rotator.html', {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
        'error': error,
        'mode': mode,
        'playlist_id': playlist_id,
    })


class Playlist:
    def __init__(self, playlist_json):
        self.id = playlist_json['id']
        self.title = playlist_json['name']
        self.album_art_url = get_cover_art_url(playlist_json)


def display_playlists(request):
    try:
        client = spotify(request)
    except AttributeError as e:
        return HttpResponseRedirect(e.args[0])
    playlists = followed_playlists(client)
    playlists = [Playlist(playlist) for playlist in playlists['items']]
    return render(request, 'display_playlists.html', {'playlists': playlists, 'mode': 'playlist'})

def callback(request):
    token_callback(request)
    return HttpResponseRedirect('/')

def login(request):
    try:
        get_token(request)
    except AttributeError as e:
        return HttpResponseRedirect(e.args[0])
    return HttpResponseRedirect('/')

def logout(request):
    client_logout(request)
    return HttpResponseRedirect('/login')


@require_http_methods(['GET', 'POST'])
def setup(request):
    if request.method == 'POST':
        username = request.POST.get('lastfm_username', '').strip()
        response = HttpResponseRedirect('/')
        if username:
            response.set_cookie('lastfm_username', username, max_age=31536000)
        else:
            response.delete_cookie('lastfm_username')
        return response

    current_username = get_lastfm_username(request)
    return render(request, 'setup.html', {
        'current_username': current_username,
        'mode': 'setup',
    })
