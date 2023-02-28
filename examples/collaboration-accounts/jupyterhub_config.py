c = get_config()  # noqa

# toy config for example
# you will use a real authenticator and Spawner
c.JupyterHub.authenticator_class = "dummy"
# note: which Spawner you choose will determine some of what the collaboration account needs
# if it's LocalProcessSpawner or systemd,
# a real system user must be created.
# other spawners (simple, docker, kubernetes) do not need system users to exist
c.JupyterHub.spawner_class = "simple"

c.JupyterHub.log_level = 10
c.JupyterHub.cleanup_servers = True

c.JupyterHub.load_roles = []

c.JupyterHub.load_groups = {
    # collaborative accounts get added to this group
    "collaborative": [],
}

from pathlib import Path

import yaml

projects_yaml = Path(__file__).parent.resolve().joinpath("projects.yaml")
with projects_yaml.open() as f:
    project_config = yaml.safe_load(f)

for project_name, project in project_config["projects"].items():
    members = project.get("members", [])
    print(f"Adding project {project_name} with members {members}")
    c.JupyterHub.load_groups[project_name] = members
    collab_user = f"{project_name}-collab"
    c.JupyterHub.load_groups["collaborative"].append(collab_user)
    c.JupyterHub.load_roles.append(
        {
            "name": f"collab-access-{project_name}",
            "scopes": [
                "admin-ui",
                f"admin:servers!user={collab_user}",
                f"list:users!user={collab_user}",
                f"access:servers!user={collab_user}",
            ],
            "groups": [project_name],
        }
    )


c.JupyterHub.bind_url = "http://127.0.0.1:8000/rtc/"

# default to hub home instead of spawning
c.JupyterHub.default_url = "/rtc/hub/home"


def pre_spawn_hook(spawner):
    group_names = {group.name for group in spawner.user.groups}
    if "collaborative" in group_names:
        spawner.log.info(f"Enabling RTC for user {spawner.user.name}")
        spawner.args.append("--LabApp.collaborative=True")


c.Spawner.pre_spawn_hook = pre_spawn_hook
