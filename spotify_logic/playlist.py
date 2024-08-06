import random


def followed_playlists(client):
    playlist_list = []
    playlists = client.current_user_playlists(limit=50)
    playlist_list.extend(playlists['items'])
    _next = playlists['next']
    while _next:
        playlists = client.next(playlists)
        playlist_list.extend(playlists['items'])
        _next = playlists
    return playlists


def get_playlist(client, playlist_id):
    return client.playlist(playlist_id)['tracks']['items']


def get_random_album_from_playlist(client, playlist_id) -> tuple[str, dict, list[dict]]:
    items = get_playlist(client, playlist_id)

    albums = {
        item['track']['album']['id']: item['track']['album']
        for item in items
    }

    picks = min(8, len(albums))
    album = random.sample(list(albums.values()), k=picks)
    picked_album = album[0]
    other_albums = album[1:]
    return picked_album['artists'][0]['name'], picked_album, other_albums
