from dataclasses import dataclass

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from main import (
    get_album,
    get_random_artist_album_list,
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
    def from_album_list(album_list):
        view_albums = []
        for album in album_list['items']:
            view_albums.append(Album(
                id=album['id'],
                artist=album['artists'][0]['name'],
                title=album['name'],
                album_art_url=album['images'][0]['url']
            ))
        return view_albums


def display_albums(request):
    artist, albums = get_random_artist_album_list()
    view_albums = Album.from_album_list(albums)

    artist_name = artist['name']

    return render(request, 'display_albums.html', {'albums': view_albums, 'artist':artist_name})


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
    queue_tracks(album)

    _, albums = get_random_artist_album_list()
    view_albums = Album.from_album_list(albums)

    return render(request, 'album_rotator.html', {'albums': view_albums})
