from spotify_logic.client import spotify


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
