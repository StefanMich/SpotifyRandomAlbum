from django.urls import path

from .views import (
    callback,
    display_albums,
    display_from_playlist,
    display_playlists,
    login,
    logout,
    queue_album,
)

urlpatterns = [
    path('', display_albums, name='display_albums'),
    path('albums/', display_albums, name='display_albums'),
    path('playlists/', display_playlists, name='display_playlists'),
    path(
        'playlist_albums/<str:playlist_id>',
        display_from_playlist,
        name='display_playlist_albums'
    ),
    path('queue_album/<str:album_id>/', queue_album, name='queue_album'),
    path('callback/', callback, name='callback'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout')
]
