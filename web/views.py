from dataclasses import dataclass

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .models import Task


def display_tasks(request):
    tasks = Task.objects.all()
    return render(request, 'display_tasks.html', {'tasks': tasks})


@dataclass
class Album:
    id: int
    title: str
    url: str


def display_albums(request):
    test = "https://upload.wikimedia.org/wikipedia/en/8/83/Slayer_-_Show_No_Mercy.jpg"
    albums = [
        Album(1, 'Album 1', test),
        Album(2, 'Album 2', test),
        Album(3, 'Album 3', test),
    ]
    return render(request, 'display_albums.html', {'albums': albums})

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
