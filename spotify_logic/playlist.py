import random

from main import spotify


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


def get_playlist(playlist_id):
    return spotify.playlist(playlist_id)['tracks']['items']


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
