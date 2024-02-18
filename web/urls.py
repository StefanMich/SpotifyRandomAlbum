from django.urls import path

from .views import (
    delete_task,
    create_task,
    display_albums,
    display_tasks,
)

urlpatterns = [
    path('tasks/', display_tasks, name='display_tasks'),
    path('albums/', display_albums, name='display_albums'),
    path('tasks/<int:id>/delete/', delete_task, name='delete_task'),
    path('tasks/create/', create_task, name='create_task'),
]
