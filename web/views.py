from dataclasses import dataclass

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from main import get_album_list
from .models import Task


def display_tasks(request):
    tasks = Task.objects.all()
    return render(request, 'display_tasks.html', {'tasks': tasks})


@dataclass
class Album:
    artist: str
    title: str
    url: str


def display_albums(request):
    albums = get_album_list()

    view_albums = []
    for album in albums['items']:
        view_albums.append(Album(artist=album['artists'][0]['name'], title=album['name'], url=album['images'][0]['url']))
    return render(request, 'display_albums.html', {'albums': view_albums})



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
