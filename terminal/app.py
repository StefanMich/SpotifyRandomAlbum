import argparse
import sys

import spotipy
from spotify_logic.artist import followed_artists
from spotify_logic.album import (
    album_description,
    get_album,
    get_random_album,
    queue_tracks,
)
from spotify_logic.playlist import get_random_album_from_playlist


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

    def get_next_album(self, client, artist_list):
        if arguments.playlist:
            _, album, _ = get_random_album_from_playlist(arguments.playlist)
            album_id = album['id']
        else:
            album_id = get_random_album(artist_list)
        self.next_album = get_album(client, album_id)
        return self.next_album

    def skip_album(self):
        artist_list = followed_artists()
        self.get_next_album(artist_list)
        self.print_album()

    def print_album(self):
        print(f'Next album: {album_description(self.next_album)}')

    def next_album_from_artist(self, client):
        self.get_next_album(client, [self.next_album_artist])
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
