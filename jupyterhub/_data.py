"""Get the data files for this package."""

def get_data_files():
    """Walk up until we find share/jupyter"""
    import os
    path = os.path.abspath(os.path.dirname(__file__))
    while path != '/':
        share_jupyter = os.path.join(path, 'share', 'jupyter')
        if os.path.exists(share_jupyter):
            return share_jupyter
        path, _ = os.path.split(path)
    return ''


# Package managers can just override this with the appropriate constant
DATA_FILES_PATH = get_data_files()

