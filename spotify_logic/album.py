import random
from time import sleep

from exception_parser import parse_exception
from spotify_logic.client import (
    spotify,
)
from spotify_logic.artist import followed_artists


def get_album(album_id):
    return spotify.album(album_id)


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


def album_description(album):
    name = album["name"]
    album = album["artists"][0]["name"]
    return f"'{name}' by '{album}'"


def queue_tracks(album):
    print(f'Queueing {album_description(album)}\n')
    for track in album['tracks']['items']:
        try:
            spotify.add_to_queue(track['uri'])
        except Exception as e:
            raise parse_exception(e)
        sleep(1)  # without this, tracks might be queued in wrong order.
        # Find better way to ensure correct order
