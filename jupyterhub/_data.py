"""Get the data files for this package."""


def get_data_files():
    """Walk up until we find share/jupyter/hub"""
    import sys
    from os.path import join, abspath, dirname, exists, split
    path = abspath(dirname(__file__))
    starting_points = [path]
    if not path.startswith(sys.prefix):
        starting_points.append(sys.prefix)
    for path in starting_points:
        # walk up, looking for prefix/share/jupyter
        while path != '/':
            share_jupyter = join(path, 'share', 'jupyter', 'hub')
            if exists(join(share_jupyter, 'static', 'components')):
                return share_jupyter
            path, _ = split(path)
    # didn't find it, give up
    return ''


# Package managers can just override this with the appropriate constant
DATA_FILES_PATH = get_data_files()
