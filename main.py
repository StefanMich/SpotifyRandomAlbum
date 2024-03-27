#!/usr/bin/env python3
import argparse
import sys
import threading

import random
from time import sleep

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from exception_parser import parse_exception


scope = 'user-library-read user-read-playback-state user-modify-playback-state user-follow-read'
spotify = spotipy.Spotify(client_credentials_manager=SpotifyOAuth(scope=scope))


def album_duration_seconds(album):
    total_ms = sum(track['duration_ms'] for track in album['tracks']['items'])
    return total_ms / 1000


def get_playlist(playlist_id):
    return spotify.playlist(playlist_id)['tracks']['items']


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


def get_random_album_from_playlist(playlist_id) -> tuple[str, dict, list[dict]]:
    items = get_playlist(playlist_id)

    albums = {
        item['track']['album']['id']: item['track']['album']
        for item in items
    }

    picks = min(8, len(albums))
    album = random.sample(list(albums.values()), k=picks)
    picked_album = album[0]
    other_albums = album[1:]
    return picked_album['artists'][0]['name'], picked_album, other_albums


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


def followed_playlists():
    playlist_list = []
    playlists = spotify.current_user_playlists(limit=50)
    playlist_list.extend(playlists['items'])
    _next = playlists['next']
    while _next:
        playlists = spotify.next(playlists)
        playlist_list.extend(playlists['items'])
        _next = playlists
    return playlists


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


class Main:
    @property
    def next_album_artist(self):
        return self.next_album['artists'][0]

    @property
    def actions(self):
        return {
            'S': ('Skip Album', self.skip_album),
            'A': ('Random album from artist', self.next_album_from_artist),
            'C': ('Queue now', self.queue_now),
            'X': ('Exit', self.exit),
        }

    def run(self):
        print('SpotifyRandomAlbum!')

        self.skip_album()
        while True:
            print("------------------")
            for key, (description, _) in self.actions.items():
                print(f'{key} - {description}')
            print("------------------")
            choice = input()

            _, action = self.actions.get(choice.upper(), (None, None))
            if action:
                try:
                    action()
                except StopIteration:
                    break
            else:
                print('Unknown action')

    def queuer(self):
        try:
            queue_tracks(self.next_album)
        except spotipy.SpotifyException:
            print(
                'No active device. Please start a device, then press '
                'enter')
            input()
            queue_tracks(self.next_album)
        self.skip_album()

    def get_next_album(self, artist_list):
        if arguments.playlist:
            _, album, _ = get_random_album_from_playlist(arguments.playlist)
            album_id = album['id']
        else:
            album_id = get_random_album(artist_list)
        self.next_album = get_album(album_id)
        return self.next_album

    def skip_album(self):
        artist_list = followed_artists()
        self.get_next_album(artist_list)
        self.print_album()

    def print_album(self):
        print(f'Next album: {album_description(self.next_album)}')

    def next_album_from_artist(self):
        self.get_next_album([self.next_album_artist])
        self.print_album()

    def queue_now(self):
        self.queuer()

    def exit(self):
        raise StopIteration


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='')

    parser.add_argument(
        '--playlist',
        help='The id of the playlist to grab random albums from')

    arguments = parser.parse_args()

    try:
        Main().run()
    except KeyboardInterrupt:
        sys.exit()
