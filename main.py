import argparse
from dotenv import load_dotenv
import random
from time import sleep

import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

scope = 'user-library-read user-read-playback-state user-modify-playback-state user-follow-read'
spotify = spotipy.Spotify(client_credentials_manager=SpotifyOAuth(scope=scope))


def album_duration_seconds(album_id):
    return sum(track['duration_ms'] for track in
        spotify.album(album_id)['tracks']['items']) / 1000


def get_playlist(playlist_id):
    return spotify.playlist(playlist_id)['tracks']['items']


def get_album(album_id):
    return spotify.album(album_id)


def queue_tracks(tracks):
    for track in tracks['items']:
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
    picked_artist = random.choice(artist_list)
    albums = spotify.artist_albums(
        picked_artist['id'], album_type='album')
    return random.choice(albums['items'])['id']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='')

    parser.add_argument(
        '--playlist',
        help='The id of the playlist to grab random albums from')

    arguments = parser.parse_args()

    while True:
        if arguments.playlist:
            album_id = get_random_album_from_playlist(arguments.playlist)
        else:
            album_id = get_random_album_from_followed_artists()

        album = get_album(album_id)
        print('Queuing album: {} by {}'.format(album['name'], album['artists'][0]['name']))
        try:
            queue_tracks(album['tracks'])
        except spotipy.SpotifyException:
            print('No active device. Please start a device, then press enter')
            input()
            queue_tracks(album['tracks'])

        duration = album_duration_seconds(album_id)
        print('Waiting {} seconds for next queue'.format(duration))
        sleep(duration)

