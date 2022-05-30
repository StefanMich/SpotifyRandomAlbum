#!/usr/bin/env python3
import argparse
import sys
import threading

from dotenv import load_dotenv
import random
from time import sleep

import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

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
    print('Queueing {}'.format(album_description(album)))
    for track in album['tracks']['items']:
        spotify.add_to_queue(track['uri'])
        sleep(1)  # without this, tracks might be queued in wrong order.
        # Find better way to ensure correct order


def get_random_album_from_playlist(playlist_id):
    # 6hftFUuWJWWYHUATbia7Z1
    items = get_playlist(playlist_id)
    item = random.choice(items)
    return item['track']['album']['id']


def get_random_album_from_followed_artists():
    artist_list = []
    artists = spotify.current_user_followed_artists(limit=50)['artists']
    artist_list.extend(artists['items'])
    after = artists['cursors']['after']
    while after:
        artists = spotify.current_user_followed_artists(
            limit=50, after=after)['artists']
        artist_list.extend(artists['items'])
        after = artists['cursors']['after']
    while True:
        picked_artist = random.choice(artist_list)
        albums = spotify.artist_albums(
            picked_artist['id'], album_type='album')
        if albums['items']:
            break
    return random.choice(albums['items'])['id']


def album_description(album):
    return '\'{}\' by \'{}\''.format(album['name'], album['artists'][0]['name'])


class Main:

    def __init__(self):
        self.queue_done = threading.Event()
        self.requeue = threading.Event()
        self.next_album = None

    @property
    def actions(self):
        return {
            'S': ('Skip Album', self.skip_album),
            'C': ('Queue now', self.queue_now),
            'X': ('Exit', self.exit),
        }

    def run(self):
        print('SpotifyRandomAlbum!')
        choice = ''
        while choice.upper() != 'C':
            self.get_next_album()
            print('Queue album: {}'.format(album_description(self.next_album)))
            choice = input('Continue (C) or Skip (S)?')

        queuer = threading.Thread(target=self.queuer, daemon=True)
        queuer.start()

        self.queue_done.wait()
        while True:
            print("------------------")
            for key, (description, _) in self.actions.items():
                print(f'{key} - {description}')
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
        while True:
            self.queue_done.clear()
            try:
                queue_tracks(self.next_album)
            except spotipy.SpotifyException:
                print(
                    'No active device. Please start a device, then press '
                    'enter')
                input()
                queue_tracks(self.next_album)

            duration = album_duration_seconds(self.next_album)
            self.get_next_album()
            print('Waiting {} seconds to queue {}'.format(
                duration, album_description(self.next_album)))
            self.queue_done.set()
            self.requeue.wait(duration)
            self.requeue.clear()

    def get_next_album(self):
        if arguments.playlist:
            album_id = get_random_album_from_playlist(arguments.playlist)
        else:
            album_id = get_random_album_from_followed_artists()
        self.next_album = get_album(album_id)

    def skip_album(self):
        self.get_next_album()
        print('Next album: {}'.format(album_description(self.next_album)))

    def queue_now(self):
        self.requeue.set()
        print('Queuing now')
        self.queue_done.wait()
        return

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
