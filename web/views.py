from dataclasses import dataclass
import random

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from exception_parser import SpotifyException
from main import (
    get_album,
    get_random_album_from_playlist,
    get_random_artist_album_list,
    get_saved_albums,
    queue_tracks,
)
from .models import Task


def display_tasks(request):
    tasks = Task.objects.all()
    return render(request, 'display_tasks.html', {'tasks': tasks})


@dataclass
class Album:
    id: str
    artist: str
    title: str
    album_art_url: str

    @staticmethod
    def from_spotify_album(album):
        return Album(
            id=album['id'],
            artist=album['artists'][0]['name'],
            title=album['name'],
            album_art_url=album['images'][0]['url']
        )

    @staticmethod
    def from_album_list(album_list):
        view_albums = []
        for album in album_list:
            view_albums.append(Album.from_spotify_album(album))
        return view_albums


@require_http_methods(['GET'])
def display_albums(request):
    artist_name, other_albums, spotlight_album = prepare_albums()

    return render(request, 'display_albums.html', {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
    })


def prepare_albums():
    artist, albums = get_random_artist_album_list()
    saved = get_saved_albums(albums)
    weights = [3 if is_saved else 1 for is_saved in saved]

    view_albums = Album.from_album_list(albums)
    spotlight_album = random.choices(view_albums, weights=weights)[0]
    other_albums = [album for album in view_albums if album.id != spotlight_album.id]
    artist_name = artist['name']
    return artist_name, other_albums, spotlight_album


@require_http_methods(['GET'])
def display_from_playlist(request, playlist_id):
    artist_name, spotlight_album, other_albums = prepare_from_playlist(
        playlist_id)

    return render(request, 'display_albums.html', {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
    })


def prepare_from_playlist(playlist_id):
    artist_name, album, other = get_random_album_from_playlist(playlist_id)
    return artist_name, Album.from_spotify_album(album), Album.from_album_list(other)


@require_http_methods(['DELETE'])
def delete_task(request, id):
    Task.objects.filter(id=id).delete()
    tasks = Task.objects.all()
    return render(request, 'tasks_list.html', {'tasks': tasks})


@require_http_methods(['POST'])
def create_task(request):
    t = Task(
        title=request.POST['title'],
        description=request.POST['description'],
    )
    t.clean()
    t.save()
    tasks = Task.objects.all()
    return render(request, 'tasks_list.html', {'tasks': tasks})


@require_http_methods(['POST'])
def queue_album(request, album_id):
    album = get_album(album_id)
    error = None
    try:
        queue_tracks(album)
    except SpotifyException as e:
        error = e.args[0]

    artist_name, other_albums, spotlight_album = prepare_albums()

    return render(request, 'album_rotator.html', {
        'spotlight_album': spotlight_album,
        'other_albums': other_albums,
        'artist': artist_name,
        'error': error,
    })
