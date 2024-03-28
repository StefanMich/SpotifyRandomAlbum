#!/usr/bin/env python3
import random
from time import sleep

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from exception_parser import parse_exception

scope = 'user-library-read user-read-playback-state user-modify-playback-state user-follow-read'
spotify = spotipy.Spotify(client_credentials_manager=SpotifyOAuth(scope=scope))


def get_album(album_id):
    return spotify.album(album_id)


def queue_tracks(album):
    print(f'Queueing {album_description(album)}\n')
    for track in album['tracks']['items']:
        try:
            spotify.add_to_queue(track['uri'])
        except Exception as e:
            raise parse_exception(e)
        sleep(1)  # without this, tracks might be queued in wrong order.
        # Find better way to ensure correct order


def get_random_album(artists):
    while True:
        picked_artist = random.choice(artists)
        albums = spotify.artist_albums(
            picked_artist['id'], album_type='album')
        if albums['items']:
            break
    return random.choice(albums['items'])['id']


def get_random_artist_album_list():
    artist_list = followed_artists()
    picked_artist = random.choice(artist_list)
    albums = spotify.artist_albums(
        picked_artist['id'], album_type='album')['items']
    return picked_artist, albums


def get_saved_albums(albums):
    saved = spotify.current_user_saved_albums_contains(
        [album['id'] for album in albums])
    return saved


def followed_artists():
    artist_list = []
    artists = spotify.current_user_followed_artists(limit=50)['artists']
    artist_list.extend(artists['items'])
    after = artists['cursors']['after']
    while after:
        artists = spotify.current_user_followed_artists(
            limit=50, after=after)['artists']
        artist_list.extend(artists['items'])
        after = artists['cursors']['after']
    return artist_list


def album_description(album):
    name = album["name"]
    album = album["artists"][0]["name"]
    return f"'{name}' by '{album}'"
