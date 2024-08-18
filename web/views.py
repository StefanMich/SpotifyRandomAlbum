from dataclasses import dataclass
from enum import Enum
import logging
import random

from django.http import HttpResponseRedirect
from django.shortcuts import render
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
)
from spotify_logic.playlist import (
    followed_playlists,
    get_random_album_from_playlist,
)

logger = logging.getLogger(__name__)

@dataclass
class Album:
    id: str
    artist: str
    title: str
    album_art_url: str

    @staticmethod
    def from_spotify_album(album):
        return Album(
            id=album['id'],
            artist=album['artists'][0]['name'],
            title=album['name'],
            album_art_url=album['images'][0]['url']
        )

    @staticmethod
    def from_album_list(album_list):
        view_albums = []
        for album in album_list:
            view_albums.append(Album.from_spotify_album(album))
        return view_albums


@require_http_methods(['GET'])
def display_albums(request):
    try:
        client = spotify(request)
    except AttributeError as e:
        return HttpResponseRedirect(e.args[0])
    artist_name, other_albums, spotlight_album = prepare_albums(client)

    return render(request, 'display_albums.html', {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
        'mode': 'album',
    })


def prepare_albums(client, unused=None):
    artist, albums = get_random_artist_album_list(client)
    logger.debug(f'Preparing artist: {artist["name"]} {artist["id"]}')
    saved = get_saved_albums(client, albums)
    weights = [3 if is_saved else 1 for is_saved in saved]

    view_albums = Album.from_album_list(albums)
    spotlight_album = random.choices(view_albums, weights=weights)[0]
    other_albums = [album for album in view_albums if album.id != spotlight_album.id]
    artist_name = artist['name']
    return artist_name, other_albums, spotlight_album


@require_http_methods(['GET'])
def display_from_playlist(request, playlist_id):
    client = spotify(request)
    artist_name, other_albums, spotlight_album = prepare_from_playlist(
        client, playlist_id)

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


def prepare_from_playlist(client, playlist_id):
    artist_name, album, other = get_random_album_from_playlist(client, playlist_id)
    return artist_name, Album.from_album_list(other), Album.from_spotify_album(album)


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
    mode_func = Mode(mode).func

    artist_name, other_albums, spotlight_album = mode_func(client, playlist_id)

    return render(request, 'album_rotator.html', {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
        'error': error,
        'mode': mode,
        'playlist_id': playlist_id,
    })


@dataclass
class Playlist:
    id: str
    title: str
    album_art_url: str


def display_playlists(request):
    client = spotify(request)
    playlists = followed_playlists(client)
    playlists = [Playlist(
        id=playlist['id'],
        title=playlist['name'],
        album_art_url=playlist['images'][0]['url'],
    ) for playlist in playlists['items']]
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
