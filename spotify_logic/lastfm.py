import json
import logging
import os
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

LASTFM_API_KEY = os.getenv('LASTFM_API_KEY')
LASTFM_BASE_URL = 'http://ws.audioscrobbler.com/2.0/'


def get_album_playcount(artist: str, album: str, username: Optional[str] = None) -> Optional[int]:
    """
    Get playcount for an album from last.fm API.

    Args:
        artist: Artist name
        album: Album name
        username: Last.fm username (optional)

    Returns:
        Playcount as integer, or None if not found or error occurs
    """
    if not LASTFM_API_KEY:
        logger.warning('LASTFM_API_KEY not set in environment')
        return None

    if not username:
        return None

    params = {
        'method': 'album.getinfo',
        'api_key': LASTFM_API_KEY,
        'artist': artist,
        'album': album,
        'format': 'json',
        'username': username,
    }

    query_string = urllib.parse.urlencode(params)
    url = f'{LASTFM_BASE_URL}?{query_string}'

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            if 'album' in data and 'userplaycount' in data['album']:
                playcount = data['album']['userplaycount']
                return int(playcount) if playcount else 0
            return None
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.debug(f'Error fetching playcount for {artist} - {album}: {e}')
        return None

