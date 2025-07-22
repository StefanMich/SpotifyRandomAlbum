#!/bin/bash

# Run migrations
python manage.py migrate

# Start gunicorn
gunicorn SpotifyRandomAlbum.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
