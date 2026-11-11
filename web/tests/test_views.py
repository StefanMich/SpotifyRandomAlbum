from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve, reverse

from spotify_logic.client import get_token, token_callback
from web.views import (
    Album,
    Mode,
    display_albums,
    prepare_albums,
    prepare_from_playlist,
)


def _album_json(
    album_id: str = 'alb-1',
    name: str = 'Kind of Blue',
    artist: str = 'Miles Davis',
    image: str | None = 'http://cover',
) -> dict:
    images = [] if image is None else [{'url': image}]
    return {
        'id': album_id,
        'name': name,
        'artists': [{'name': artist}] if artist else [],
        'images': images,
    }


def _view_album(
    album_id: str = 'alb-1',
    title: str = 'Kind of Blue',
    artist: str = 'Miles Davis',
    playcount: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=album_id,
        title=title,
        artist=artist,
        album_art_url='http://cover',
        playcount=playcount,
    )


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    STATICFILES_STORAGE=(
        'django.contrib.staticfiles.storage.StaticFilesStorage'
    ),
)
class AlbumModelTests(SimpleTestCase):
    def test_album_object_reads_title_artist_and_cover(self) -> None:
        with patch('web.views.get_album_playcount', return_value=4):
            album = Album(_album_json(), 'listener')

        self.assertEqual(album.title, 'Kind of Blue')
        self.assertEqual(album.artist, 'Miles Davis')
        self.assertEqual(album.id, 'alb-1')
        self.assertEqual(album.album_art_url, 'http://cover')
        self.assertEqual(album.playcount, 4)

    def test_missing_cover_and_artist_use_fallbacks(self) -> None:
        payload = _album_json(artist='', image=None)
        with patch('web.views.get_album_playcount', return_value=None):
            album = Album(payload)

        self.assertEqual(album.artist, 'Unknown Artist')
        self.assertIn('no_cover_art.jpg', album.album_art_url)
        self.assertIsNone(album.playcount)

    def test_playlist_track_uses_nested_album_fields(self) -> None:
        payload = {
            'images': [{'url': 'http://track-cover'}],
            'track': {
                'artists': [{'name': 'Track Artist'}],
                'album': {'name': 'Track Album', 'id': 'track-alb'},
            },
        }
        with patch('web.views.get_album_playcount', return_value=None):
            album = Album(payload)

        self.assertEqual(album.title, 'Track Album')
        self.assertEqual(album.id, 'track-alb')
        self.assertEqual(album.artist, 'Track Artist')
        self.assertEqual(album.album_art_url, 'http://track-cover')

    def test_saved_albums_are_weighted_higher(self) -> None:
        albums = [
            _album_json('saved', 'Saved', 'Artist'),
            _album_json('other', 'Other', 'Artist'),
        ]
        seen: dict[str, list[int]] = {}

        def choose(
            population: list[Album],
            weights: list[int],
        ) -> list[Album]:
            seen['weights'] = weights
            return [population[0]]

        with patch(
            'web.views.get_random_artist_album_list',
            return_value=({'name': 'Artist', 'id': 'art'}, albums),
        ), patch(
            'web.views.get_saved_albums',
            return_value=[True, False],
        ), patch(
            'web.views.get_album_playcount',
            return_value=None,
        ), patch(
            'web.views.random.choices',
            side_effect=choose,
        ):
            artist, others, spotlight = prepare_albums(object(), 'listener')

        self.assertEqual(artist, 'Artist')
        self.assertEqual(seen['weights'], [3, 1])
        self.assertEqual(spotlight.id, 'saved')
        self.assertEqual([album.id for album in others], ['other'])

    def test_artist_with_no_albums_is_skipped(self) -> None:
        albums = [_album_json()]
        with patch(
            'web.views.get_random_artist_album_list',
            side_effect=[
                ({'name': 'Empty', 'id': '0'}, []),
                ({'name': 'Miles Davis', 'id': '1'}, albums),
            ],
        ), patch(
            'web.views.get_saved_albums',
            return_value=[False],
        ), patch(
            'web.views.get_album_playcount',
            return_value=None,
        ), patch(
            'web.views.random.choices',
            side_effect=lambda population, weights: [population[0]],
        ):
            artist, others, spotlight = prepare_albums(object())

        self.assertEqual(artist, 'Miles Davis')
        self.assertEqual(spotlight.title, 'Kind of Blue')
        self.assertEqual(others, [])

    def test_playlist_preparation_wraps_each_album(self) -> None:
        spotlight = _album_json('spot', 'Spotlight')
        other = _album_json('other', 'Other')
        with patch(
            'web.views.get_random_album_from_playlist',
            return_value=('Miles Davis', spotlight, [other]),
        ), patch(
            'web.views.get_album_playcount',
            return_value=2,
        ):
            artist, others, album = prepare_from_playlist(
                object(), 'playlist-1', 'listener')

        self.assertEqual(artist, 'Miles Davis')
        self.assertEqual(album.id, 'spot')
        self.assertEqual(album.playcount, 2)
        self.assertEqual([item.id for item in others], ['other'])

    def test_mode_selects_the_album_or_playlist_loader(self) -> None:
        self.assertIs(Mode.ALBUM.func, prepare_albums)
        self.assertIs(Mode('playlist').func, prepare_from_playlist)
        self.assertEqual(Mode.ALBUM.value, 'album')
        with self.assertRaises(ValueError):
            Mode('nope')


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    STATICFILES_STORAGE=(
        'django.contrib.staticfiles.storage.StaticFilesStorage'
    ),
)
class ViewTests(SimpleTestCase):
    def test_routes_point_at_the_album_views(self) -> None:
        self.assertIs(resolve('/').func, display_albums)
        self.assertIs(resolve('/albums/').func, display_albums)
        self.assertEqual(
            reverse('queue_album', args=['abc']),
            '/queue_album/abc/',
        )
        self.assertEqual(
            reverse('display_playlist_albums', args=['playlist-1']),
            '/playlist_albums/playlist-1',
        )

    def test_setup_shows_and_stores_the_lastfm_username(self) -> None:
        self.client.cookies['lastfm_username'] = 'listener'
        shown = self.client.get('/setup/')
        self.assertContains(shown, 'value="listener"')

        saved = self.client.post('/setup/', {'lastfm_username': '  stefan  '})
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(saved['Location'], '/')
        self.assertEqual(saved.cookies['lastfm_username'].value, 'stefan')
        self.assertEqual(saved.cookies['lastfm_username']['max-age'], 31536000)

    def test_blank_setup_username_clears_the_cookie(self) -> None:
        cleared = self.client.post('/setup/', {'lastfm_username': '   '})

        self.assertEqual(cleared.cookies['lastfm_username'].value, '')
        self.assertEqual(cleared.cookies['lastfm_username']['max-age'], 0)

    def test_login_redirects_to_spotify_when_there_is_no_token(self) -> None:
        with patch('spotify_logic.client.SpotifyOAuth') as oauth_cls:
            oauth_cls.return_value.get_cached_token.return_value = None
            oauth_cls.return_value.get_authorize_url.return_value = (
                'https://accounts.spotify.com/authorize?x=1'
            )
            response = self.client.get('/login/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://accounts.spotify.com/authorize?x=1',
        )

    def test_login_continues_home_when_a_token_is_cached(self) -> None:
        with patch('spotify_logic.client.SpotifyOAuth') as oauth_cls:
            oauth_cls.return_value.get_cached_token.return_value = {
                'access_token': 'tok',
            }
            response = self.client.get('/login/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_get_token_returns_the_cached_access_token(self) -> None:
        request = RequestFactory().get('/login/')
        with patch('spotify_logic.client.SpotifyOAuth') as oauth_cls:
            oauth_cls.return_value.get_cached_token.return_value = {
                'access_token': 'tok',
            }
            token = get_token(request)

        self.assertEqual(token, 'tok')

    def test_callback_exchanges_the_code_for_a_token(self) -> None:
        request = RequestFactory().get('/callback/', {'code': 'auth-code'})
        with patch('spotify_logic.client.SpotifyOAuth') as oauth_cls, patch(
            'spotify_logic.client.spotipy.Spotify',
        ) as spotify_cls:
            oauth = oauth_cls.return_value
            oauth.parse_response_code.return_value = 'auth-code'
            oauth.get_access_token.return_value = {'access_token': 'tok'}
            token_callback(request)

        oauth.get_access_token.assert_called_once_with('auth-code')
        spotify_cls.assert_called_once_with(auth='tok')

    def test_callback_sends_the_user_home(self) -> None:
        with patch('web.views.token_callback') as callback:
            response = self.client.get('/callback/', {'code': 'auth-code'})

        callback.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_logout_forgets_the_token(self) -> None:
        with patch(
            'spotify_logic.client.DjangoSessionCacheHandler',
        ) as cache_cls:
            response = self.client.get('/logout/')

        cache_cls.return_value.save_token_to_cache.assert_called_once_with(
            'INVALID')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/login')

    def test_albums_page_redirects_until_the_user_logs_in(self) -> None:
        with patch(
            'web.views.spotify',
            side_effect=AttributeError('https://accounts.spotify.com/authorize'),
        ):
            response = self.client.get('/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://accounts.spotify.com/authorize',
        )

    def test_albums_page_renders_the_spotlight_album(self) -> None:
        spotlight = _view_album(playcount=9)
        other = _view_album('alb-2', 'Other', playcount=None)
        with patch('web.views.spotify') as spotify, patch(
            'web.views.prepare_albums',
            return_value=('Miles Davis', [other], spotlight),
        ) as prepare:
            self.client.cookies['lastfm_username'] = 'listener'
            response = self.client.get('/albums/')

        prepare.assert_called_once_with(spotify.return_value, 'listener')
        self.assertContains(response, 'Kind of Blue')
        self.assertContains(response, 'Miles Davis')
        self.assertContains(response, 'playcount-bubble')
        self.assertContains(response, '>9<')
        self.assertContains(response, '/queue_album/alb-1/')

    def test_playlists_page_lists_followed_playlists(self) -> None:
        with patch('web.views.spotify'), patch(
            'web.views.followed_playlists',
            return_value={'items': [{
                'id': 'playlist-1',
                'name': 'Late Night',
                'images': [{'url': 'http://cover'}],
            }]},
        ):
            response = self.client.get('/playlists/')

        self.assertContains(response, 'Late Night')
        self.assertContains(response, '/playlist_albums/playlist-1')

    def test_playlist_page_uses_a_partial_for_htmx(self) -> None:
        spotlight = _view_album()
        with patch('web.views.spotify') as spotify, patch(
            'web.views.prepare_from_playlist',
            return_value=('Miles Davis', [], spotlight),
        ) as prepare:
            self.client.cookies['lastfm_username'] = 'listener'
            partial = self.client.get(
                '/playlist_albums/playlist-1',
                HTTP_HX_REQUEST='true',
            )
            page = self.client.get('/playlist_albums/playlist-1')

        prepare.assert_called_with(
            spotify.return_value, 'playlist-1', 'listener')
        self.assertContains(partial, 'Kind of Blue')
        self.assertNotContains(partial, 'topnav')
        self.assertContains(page, 'topnav')
        self.assertContains(page, 'Kind of Blue')

    def test_queue_album_renders_the_next_album(self) -> None:
        spotlight = _view_album('next', 'Next Album')
        with patch('web.views.spotify') as spotify, patch(
            'web.views.get_album',
            return_value={'id': 'abc'},
        ) as get_album, patch(
            'web.views.queue_tracks',
        ) as queue_tracks, patch.object(
            Mode.ALBUM,
            'func',
            return_value=('Miles Davis', [], spotlight),
        ) as prepare:
            response = self.client.post(
                '/queue_album/abc/',
                {'mode': 'album'},
            )

        get_album.assert_called_once_with(spotify.return_value, 'abc')
        queue_tracks.assert_called_once_with(
            spotify.return_value, {'id': 'abc'})
        prepare.assert_called_once_with(spotify.return_value, '', None)
        self.assertContains(response, 'Next Album')
        self.assertNotContains(response, 'class="error"')

    def test_queue_album_shows_a_device_error_and_still_rotates(self) -> None:
        from exception_parser import SpotifyException

        spotlight = _view_album('next', 'Next Album')
        with patch('web.views.spotify'), patch(
            'web.views.get_album',
            return_value={'id': 'abc'},
        ), patch(
            'web.views.queue_tracks',
            side_effect=SpotifyException(
                'No active device found. Start a device and try again.'),
        ), patch.object(
            Mode.PLAYLIST,
            'func',
            return_value=('Miles Davis', [], spotlight),
        ) as prepare:
            response = self.client.post('/queue_album/abc/', {
                'mode': 'playlist',
                'playlist_id': 'playlist-1',
            })

        prepare.assert_called_once()
        self.assertEqual(prepare.call_args.args[1], 'playlist-1')
        self.assertContains(response, 'No active device')
        self.assertContains(response, 'Next Album')

    def test_read_only_pages_reject_the_wrong_method(self) -> None:
        self.assertEqual(self.client.post('/').status_code, 405)
        self.assertEqual(
            self.client.get('/queue_album/abc/').status_code, 405)

    def test_project_imports_and_passes_system_checks(self) -> None:
        from django.core.management import call_command

        from SpotifyRandomAlbum.wsgi import application

        self.assertTrue(callable(application))
        call_command('check')
