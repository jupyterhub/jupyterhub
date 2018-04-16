"""Get the data files for this package."""
import os
import sys

_mswindows = (os.name == "nt")

def get_data_files():
    """Walk up until we find share/jupyterhub"""
    path = os.path.abspath(os.path.dirname(__file__))
    starting_points = [path]
    if not path.startswith(sys.prefix):
        starting_points.append(sys.prefix)
    if _mswindows:
        root, _ = os.path.splitdrive(path)
        root = root + '\\'
    else:
        root = '/'
    for path in starting_points:
        # walk up, looking for prefix/share/jupyter
        while path != root:
            share_jupyterhub = os.path.join(path, 'share', 'jupyterhub')
            static = os.path.join(share_jupyterhub, 'static')
            if all(os.path.exists(os.path.join(static, f)) for f in ['components', 'css']):
                return share_jupyterhub
            path, _ = os.path.split(path)
    # didn't find it, give up
    return ''


# Package managers can just override this with the appropriate constant
DATA_FILES_PATH = get_data_files()
