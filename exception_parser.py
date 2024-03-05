class SpotifyException(Exception):
    pass


def parse_exception(exception: Exception) -> Exception:
    http_status_code, code, msg = exception.args
    if 'Player command failed: No active device found' in msg:
        return SpotifyException(
            'No active device found. Start a device and try again.')
    else:
        return SpotifyException(
            f'Unknown error from the Spotify API: '
            f'Http {http_status_code} - {msg}')
