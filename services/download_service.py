import os
import tempfile

class DownloadService:
    """Service for validating and cleaning up temporary generated files."""

    def resolve_temp_path(self, path: str) -> str:
        """Validate given path is inside system temp dir and exists. Return realpath or raise.

        Raises FileNotFoundError, PermissionError on failure.
        """
        if not path:
            raise FileNotFoundError('path required')
        real = os.path.realpath(path)
        if not os.path.exists(real):
            raise FileNotFoundError('file not found')
        tmpdir = os.path.realpath(tempfile.gettempdir())
        try:
            common = os.path.commonpath([real, tmpdir])
        except Exception:
            common = ''
        if common != tmpdir:
            raise PermissionError('access to path not allowed')
        return real

    def cleanup(self, file_path: str):
        """Remove file and try remove empty parent directory."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        parent = os.path.dirname(file_path)
        try:
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        except Exception:
            pass
