from jupyterhub.singleuser import SingleUserNotebookApp
from jupyterlab.labapp import LabApp


class SingleUserLabApp(LabApp, SingleUserNotebookApp):
    pass


def main(argv=None):
    return SingleUserLabApp.launch_instance(argv)


if __name__ == "__main__":
    main()
