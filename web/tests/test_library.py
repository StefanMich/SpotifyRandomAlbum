import json
import urllib.error
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from exception_parser import SpotifyException, parse_exception
from spotify_logic.album import (
    album_description,
    get_album,
    get_random_album,
    get_saved_albums,
    queue_tracks,
)
from spotify_logic.artist import followed_artists
from spotify_logic.lastfm import get_album_playcount
from spotify_logic.playlist import (
    followed_playlists,
    get_random_album_from_playlist,
)


def _album(name: str, artist: str) -> dict:
    return {'name': name, 'artists': [{'name': artist}]}


class ExceptionParserTests(SimpleTestCase):
    def test_no_active_device_becomes_a_retry_message(self) -> None:
        error = parse_exception(Exception(
            404,
            None,
            'Player command failed: No active device found',
        ))

        self.assertIsInstance(error, SpotifyException)
        self.assertEqual(
            str(error),
            'No active device found. Start a device and try again.',
        )

    def test_other_api_errors_keep_the_status_and_message(self) -> None:
        error = parse_exception(Exception(500, None, 'server exploded'))

        self.assertIsInstance(error, SpotifyException)
        self.assertEqual(
            str(error),
            'Unknown error from the Spotify API: Http 500 - server exploded',
        )


class AlbumLogicTests(SimpleTestCase):
    def test_album_description_names_the_record_and_artist(self) -> None:
        description = album_description(
            _album('Kind of Blue', 'Miles Davis'))

        self.assertEqual(description, "'Kind of Blue' by 'Miles Davis'")

    def test_get_album_returns_the_client_payload(self) -> None:
        client = MagicMock()
        client.album.return_value = {'id': 'album-1'}

        self.assertEqual(get_album(client, 'album-1'), {'id': 'album-1'})
        client.album.assert_called_once_with('album-1')

    def test_random_album_skips_artists_with_no_albums(self) -> None:
        artists = [{'id': 'empty'}, {'id': 'full'}]
        client = MagicMock()
        client.artist_albums.side_effect = [
            {'items': []},
            {'items': [{'id': 'album-1'}, {'id': 'album-2'}]},
        ]

        with patch(
            'spotify_logic.album.random.choice',
            side_effect=[artists[0], artists[1], {'id': 'album-2'}],
        ):
            album_id = get_random_album(client, artists)

        self.assertEqual(album_id, 'album-2')
        self.assertEqual(client.artist_albums.call_count, 2)

    def test_saved_albums_are_looked_up_by_id(self) -> None:
        client = MagicMock()
        client.current_user_saved_albums_contains.return_value = [True, False]
        albums = [{'id': 'a'}, {'id': 'b'}]

        saved = get_saved_albums(client, albums)

        self.assertEqual(saved, [True, False])
        client.current_user_saved_albums_contains.assert_called_once_with(
            ['a', 'b'])

    def test_queue_tracks_sends_each_uri_in_order(self) -> None:
        client = MagicMock()
        album = {
            'name': 'Kind of Blue',
            'artists': [{'name': 'Miles Davis'}],
            'tracks': {'items': [
                {'uri': 'spotify:track:1'},
                {'uri': 'spotify:track:2'},
            ]},
        }

        with patch('spotify_logic.album.sleep') as sleep:
            queue_tracks(client, album)

        self.assertEqual(
            [call.args[0] for call in client.add_to_queue.call_args_list],
            ['spotify:track:1', 'spotify:track:2'],
        )
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(1)

    def test_queue_tracks_turns_a_device_error_into_spotify_exception(
        self,
    ) -> None:
        client = MagicMock()
        client.add_to_queue.side_effect = Exception(
            404,
            None,
            'Player command failed: No active device found',
        )
        album = {
            'name': 'Kind of Blue',
            'artists': [{'name': 'Miles Davis'}],
            'tracks': {'items': [{'uri': 'spotify:track:1'}]},
        }

        with patch('spotify_logic.album.sleep'):
            with self.assertRaises(SpotifyException) as raised:
                queue_tracks(client, album)

        self.assertIn('No active device', str(raised.exception))


class ArtistLogicTests(SimpleTestCase):
    def test_followed_artists_walks_the_cursor(self) -> None:
        client = MagicMock()
        client.current_user_followed_artists.side_effect = [
            {'artists': {
                'items': [{'id': '1'}],
                'cursors': {'after': 'cursor'},
            }},
            {'artists': {
                'items': [{'id': '2'}],
                'cursors': {'after': None},
            }},
        ]

        artists = followed_artists(client)

        self.assertEqual([artist['id'] for artist in artists], ['1', '2'])
        self.assertEqual(client.current_user_followed_artists.call_count, 2)


class PlaylistLogicTests(SimpleTestCase):
    def test_followed_playlists_returns_a_single_page(self) -> None:
        page = {'items': [{'id': 'playlist-1'}], 'next': None}
        client = MagicMock()
        client.current_user_playlists.return_value = page

        self.assertEqual(followed_playlists(client), page)
        client.next.assert_not_called()

    def test_random_playlist_album_collapses_duplicate_albums(self) -> None:
        def track(album_id: str, name: str, artist: str) -> dict:
            return {'track': {'album': {
                'id': album_id,
                'name': name,
                'artists': [{'name': artist}],
            }}}

        client = MagicMock()
        client.playlist.return_value = {'tracks': {'items': [
            track('alb-1', 'One', 'Artist One'),
            track('alb-1', 'One', 'Artist One'),
            track('alb-2', 'Two', 'Artist Two'),
        ]}}

        artist, album, others = get_random_album_from_playlist(
            client, 'playlist-1')

        returned_ids = {album['id'], *(item['id'] for item in others)}
        self.assertEqual(returned_ids, {'alb-1', 'alb-2'})
        self.assertEqual(len(others), 1)
        self.assertNotEqual(others[0]['id'], album['id'])
        self.assertEqual(artist, album['artists'][0]['name'])
        client.playlist.assert_called_once_with('playlist-1')


class LastFmTests(SimpleTestCase):
    def test_missing_api_key_returns_none(self) -> None:
        with patch('spotify_logic.lastfm.LASTFM_API_KEY', None):
            playcount = get_album_playcount('Artist', 'Album', 'listener')

        self.assertIsNone(playcount)

    def test_missing_username_returns_none(self) -> None:
        with patch('spotify_logic.lastfm.LASTFM_API_KEY', 'key'):
            playcount = get_album_playcount('Artist', 'Album', None)

        self.assertIsNone(playcount)

    def _response(self, payload: bytes) -> MagicMock:
        response = MagicMock()
        response.read.return_value = payload
        urlopen = MagicMock()
        urlopen.return_value.__enter__.return_value = response
        return urlopen

    def test_playcount_is_read_from_the_album_payload(self) -> None:
        body = json.dumps({'album': {'userplaycount': '12'}}).encode()
        with patch('spotify_logic.lastfm.LASTFM_API_KEY', 'key'), patch(
            'spotify_logic.lastfm.urllib.request.urlopen',
            self._response(body),
        ):
            playcount = get_album_playcount('Artist', 'Album', 'listener')

        self.assertEqual(playcount, 12)

    def test_blank_playcount_is_zero(self) -> None:
        body = json.dumps({'album': {'userplaycount': ''}}).encode()
        with patch('spotify_logic.lastfm.LASTFM_API_KEY', 'key'), patch(
            'spotify_logic.lastfm.urllib.request.urlopen',
            self._response(body),
        ):
            playcount = get_album_playcount('Artist', 'Album', 'listener')

        self.assertEqual(playcount, 0)

    def test_http_and_json_errors_return_none(self) -> None:
        with patch('spotify_logic.lastfm.LASTFM_API_KEY', 'key'), patch(
            'spotify_logic.lastfm.urllib.request.urlopen',
            side_effect=urllib.error.URLError('down'),
        ):
            self.assertIsNone(
                get_album_playcount('Artist', 'Album', 'listener'))

        with patch('spotify_logic.lastfm.LASTFM_API_KEY', 'key'), patch(
            'spotify_logic.lastfm.urllib.request.urlopen',
            self._response(b'not-json'),
        ):
            self.assertIsNone(
                get_album_playcount('Artist', 'Album', 'listener'))
