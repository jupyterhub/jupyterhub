import glob
import os
import re
import sys

from binascii import a2b_hex

from tornado.httpclient import AsyncHTTPClient
from kubernetes import client
from jupyterhub.utils import url_path_join

# Make sure that modules placed in the same directory as the jupyterhub config are added to the pythonpath
configuration_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, configuration_directory)

from z2jh import (
    get_config,
    set_config_if_not_none,
    get_name,
    get_name_env,
    get_secret_value,
)


def camelCaseify(s):
    """convert snake_case to camelCase

    For the common case where some_value is set from someValue
    so we don't have to specify the name twice.
    """
    return re.sub(r"_([a-z])", lambda m: m.group(1).upper(), s)


# Configure JupyterHub to use the curl backend for making HTTP requests,
# rather than the pure-python implementations. The default one starts
# being too slow to make a large number of requests to the proxy API
# at the rate required.
AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

c.JupyterHub.spawner_class = "kubespawner.KubeSpawner"

# Connect to a proxy running in a different pod. Note that *_SERVICE_*
# environment variables are set by Kubernetes for Services
c.ConfigurableHTTPProxy.api_url = (
    f'http://{get_name("proxy-api")}:{get_name_env("proxy-api", "_SERVICE_PORT")}'
)
c.ConfigurableHTTPProxy.should_start = False

# Do not shut down user pods when hub is restarted
c.JupyterHub.cleanup_servers = False

# Check that the proxy has routes appropriately setup
c.JupyterHub.last_activity_interval = 60

# Don't wait at all before redirecting a spawning user to the progress page
c.JupyterHub.tornado_settings = {
    "slow_spawn_timeout": 0,
}


# configure the hub db connection
db_type = get_config("hub.db.type")
if db_type == "sqlite-pvc":
    c.JupyterHub.db_url = "sqlite:///jupyterhub.sqlite"
elif db_type == "sqlite-memory":
    c.JupyterHub.db_url = "sqlite://"
else:
    set_config_if_not_none(c.JupyterHub, "db_url", "hub.db.url")
db_password = get_secret_value("hub.db.password", None)
if db_password is not None:
    if db_type == "mysql":
        os.environ["MYSQL_PWD"] = db_password
    elif db_type == "postgres":
        os.environ["PGPASSWORD"] = db_password
    else:
        print(f"Warning: hub.db.password is ignored for hub.db.type={db_type}")


# c.JupyterHub configuration from Helm chart's configmap
for trait, cfg_key in (
    ("concurrent_spawn_limit", None),
    ("active_server_limit", None),
    ("base_url", None),
    ("allow_named_servers", None),
    ("named_server_limit_per_user", None),
    ("authenticate_prometheus", None),
    ("redirect_to_server", None),
    ("shutdown_on_logout", None),
    ("template_paths", None),
    ("template_vars", None),
):
    if cfg_key is None:
        cfg_key = camelCaseify(trait)
    set_config_if_not_none(c.JupyterHub, trait, "hub." + cfg_key)

# hub_bind_url configures what the JupyterHub process within the hub pod's
# container should listen to.
hub_container_port = 8081
c.JupyterHub.hub_bind_url = f"http://:{hub_container_port}"

# hub_connect_url is the URL for connecting to the hub for use by external
# JupyterHub services such as the proxy. Note that *_SERVICE_* environment
# variables are set by Kubernetes for Services.
c.JupyterHub.hub_connect_url = (
    f'http://{get_name("hub")}:{get_name_env("hub", "_SERVICE_PORT")}'
)

# implement common labels
# this duplicates the jupyterhub.commonLabels helper
common_labels = c.KubeSpawner.common_labels = {}
common_labels["app"] = get_config(
    "nameOverride",
    default=get_config("Chart.Name", "jupyterhub"),
)
common_labels["heritage"] = "jupyterhub"
chart_name = get_config("Chart.Name")
chart_version = get_config("Chart.Version")
if chart_name and chart_version:
    common_labels["chart"] = "{}-{}".format(
        chart_name,
        chart_version.replace("+", "_"),
    )
release = get_config("Release.Name")
if release:
    common_labels["release"] = release

c.KubeSpawner.namespace = os.environ.get("POD_NAMESPACE", "default")

# Max number of consecutive failures before the Hub restarts itself
# requires jupyterhub 0.9.2
set_config_if_not_none(
    c.Spawner,
    "consecutive_failure_limit",
    "hub.consecutiveFailureLimit",
)

for trait, cfg_key in (
    ("pod_name_template", None),
    ("start_timeout", None),
    ("image_pull_policy", "image.pullPolicy"),
    # ('image_pull_secrets', 'image.pullSecrets'), # Managed manually below
    ("events_enabled", "events"),
    ("extra_labels", None),
    ("extra_annotations", None),
    ("uid", None),
    ("fs_gid", None),
    ("service_account", "serviceAccountName"),
    ("storage_extra_labels", "storage.extraLabels"),
    # ("tolerations", "extraTolerations"), # Managed manually below
    ("node_selector", None),
    ("node_affinity_required", "extraNodeAffinity.required"),
    ("node_affinity_preferred", "extraNodeAffinity.preferred"),
    ("pod_affinity_required", "extraPodAffinity.required"),
    ("pod_affinity_preferred", "extraPodAffinity.preferred"),
    ("pod_anti_affinity_required", "extraPodAntiAffinity.required"),
    ("pod_anti_affinity_preferred", "extraPodAntiAffinity.preferred"),
    ("lifecycle_hooks", None),
    ("init_containers", None),
    ("extra_containers", None),
    ("mem_limit", "memory.limit"),
    ("mem_guarantee", "memory.guarantee"),
    ("cpu_limit", "cpu.limit"),
    ("cpu_guarantee", "cpu.guarantee"),
    ("extra_resource_limits", "extraResource.limits"),
    ("extra_resource_guarantees", "extraResource.guarantees"),
    ("environment", "extraEnv"),
    ("profile_list", None),
    ("extra_pod_config", None),
):
    if cfg_key is None:
        cfg_key = camelCaseify(trait)
    set_config_if_not_none(c.KubeSpawner, trait, "singleuser." + cfg_key)

image = get_config("singleuser.image.name")
if image:
    tag = get_config("singleuser.image.tag")
    if tag:
        image = "{}:{}".format(image, tag)

    c.KubeSpawner.image = image

# Combine imagePullSecret.create (single), imagePullSecrets (list), and
# singleuser.image.pullSecrets (list).
image_pull_secrets = []
if get_config("imagePullSecret.automaticReferenceInjection") and get_config(
    "imagePullSecret.create"
):
    image_pull_secrets.append(get_name("image-pull-secret"))
if get_config("imagePullSecrets"):
    image_pull_secrets.extend(get_config("imagePullSecrets"))
if get_config("singleuser.image.pullSecrets"):
    image_pull_secrets.extend(get_config("singleuser.image.pullSecrets"))
if image_pull_secrets:
    c.KubeSpawner.image_pull_secrets = image_pull_secrets

# scheduling:
if get_config("scheduling.userScheduler.enabled"):
    c.KubeSpawner.scheduler_name = get_name("user-scheduler")
if get_config("scheduling.podPriority.enabled"):
    c.KubeSpawner.priority_class_name = get_name("priority")

# add node-purpose affinity
match_node_purpose = get_config("scheduling.userPods.nodeAffinity.matchNodePurpose")
if match_node_purpose:
    node_selector = dict(
        matchExpressions=[
            dict(
                key="hub.jupyter.org/node-purpose",
                operator="In",
                values=["user"],
            )
        ],
    )
    if match_node_purpose == "prefer":
        c.KubeSpawner.node_affinity_preferred.append(
            dict(
                weight=100,
                preference=node_selector,
            ),
        )
    elif match_node_purpose == "require":
        c.KubeSpawner.node_affinity_required.append(node_selector)
    elif match_node_purpose == "ignore":
        pass
    else:
        raise ValueError(
            "Unrecognized value for matchNodePurpose: %r" % match_node_purpose
        )

# Combine the common tolerations for user pods with singleuser tolerations
scheduling_user_pods_tolerations = get_config("scheduling.userPods.tolerations", [])
singleuser_extra_tolerations = get_config("singleuser.extraTolerations", [])
tolerations = scheduling_user_pods_tolerations + singleuser_extra_tolerations
if tolerations:
    c.KubeSpawner.tolerations = tolerations

# Configure dynamically provisioning pvc
storage_type = get_config("singleuser.storage.type")
if storage_type == "dynamic":
    pvc_name_template = get_config("singleuser.storage.dynamic.pvcNameTemplate")
    c.KubeSpawner.pvc_name_template = pvc_name_template
    volume_name_template = get_config("singleuser.storage.dynamic.volumeNameTemplate")
    c.KubeSpawner.storage_pvc_ensure = True
    set_config_if_not_none(
        c.KubeSpawner, "storage_class", "singleuser.storage.dynamic.storageClass"
    )
    set_config_if_not_none(
        c.KubeSpawner,
        "storage_access_modes",
        "singleuser.storage.dynamic.storageAccessModes",
    )
    set_config_if_not_none(
        c.KubeSpawner, "storage_capacity", "singleuser.storage.capacity"
    )

    # Add volumes to singleuser pods
    c.KubeSpawner.volumes = [
        {
            "name": volume_name_template,
            "persistentVolumeClaim": {"claimName": pvc_name_template},
        }
    ]
    c.KubeSpawner.volume_mounts = [
        {
            "mountPath": get_config("singleuser.storage.homeMountPath"),
            "name": volume_name_template,
        }
    ]
elif storage_type == "static":
    pvc_claim_name = get_config("singleuser.storage.static.pvcName")
    c.KubeSpawner.volumes = [
        {"name": "home", "persistentVolumeClaim": {"claimName": pvc_claim_name}}
    ]

    c.KubeSpawner.volume_mounts = [
        {
            "mountPath": get_config("singleuser.storage.homeMountPath"),
            "name": "home",
            "subPath": get_config("singleuser.storage.static.subPath"),
        }
    ]

# Inject singleuser.extraFiles as volumes and volumeMounts with data loaded from
# the dedicated k8s Secret prepared to hold the extraFiles actual content.
extra_files = get_config("singleuser.extraFiles", {})
if extra_files:
    volume = {
        "name": "files",
    }
    items = []
    for file_key, file_details in extra_files.items():
        # Each item is a mapping of a key in the k8s Secret to a path in this
        # abstract volume, the goal is to enable us to set the mode /
        # permissions only though so we don't change the mapping.
        item = {
            "key": file_key,
            "path": file_key,
        }
        if "mode" in file_details:
            item["mode"] = file_details["mode"]
        items.append(item)
    volume["secret"] = {
        "secretName": get_name("singleuser"),
        "items": items,
    }
    c.KubeSpawner.volumes.append(volume)

    volume_mounts = []
    for file_key, file_details in extra_files.items():
        volume_mounts.append(
            {
                "mountPath": file_details["mountPath"],
                "subPath": file_key,
                "name": "files",
            }
        )
    c.KubeSpawner.volume_mounts.extend(volume_mounts)

# Inject extraVolumes / extraVolumeMounts
c.KubeSpawner.volumes.extend(get_config("singleuser.storage.extraVolumes", []))
c.KubeSpawner.volume_mounts.extend(
    get_config("singleuser.storage.extraVolumeMounts", [])
)

c.JupyterHub.services = []

if get_config("cull.enabled", False):
    cull_cmd = ["python3", "-m", "jupyterhub_idle_culler"]
    base_url = c.JupyterHub.get("base_url", "/")
    cull_cmd.append("--url=http://localhost:8081" + url_path_join(base_url, "hub/api"))

    cull_timeout = get_config("cull.timeout")
    if cull_timeout:
        cull_cmd.append("--timeout=%s" % cull_timeout)

    cull_every = get_config("cull.every")
    if cull_every:
        cull_cmd.append("--cull-every=%s" % cull_every)

    cull_concurrency = get_config("cull.concurrency")
    if cull_concurrency:
        cull_cmd.append("--concurrency=%s" % cull_concurrency)

    if get_config("cull.users"):
        cull_cmd.append("--cull-users")

    if get_config("cull.removeNamedServers"):
        cull_cmd.append("--remove-named-servers")

    cull_max_age = get_config("cull.maxAge")
    if cull_max_age:
        cull_cmd.append("--max-age=%s" % cull_max_age)

    c.JupyterHub.services.append(
        {
            "name": "cull-idle",
            "admin": True,
            "command": cull_cmd,
        }
    )

for key, service in get_config("hub.services", {}).items():
    # c.JupyterHub.services is a list of dicts, but
    # hub.services is a dict of dicts to make the config mergable
    service.setdefault("name", key)

    # As the api_token could be exposed in hub.existingSecret, we need to read
    # it it from there or fall back to the chart managed k8s Secret's value.
    service.pop("apiToken", None)
    service["api_token"] = get_secret_value(f"hub.services.{key}.apiToken")

    c.JupyterHub.services.append(service)


set_config_if_not_none(c.Spawner, "cmd", "singleuser.cmd")
set_config_if_not_none(c.Spawner, "default_url", "singleuser.defaultUrl")

cloud_metadata = get_config("singleuser.cloudMetadata", {})

if cloud_metadata.get("blockWithIptables") == True:
    # Use iptables to block access to cloud metadata by default
    network_tools_image_name = get_config("singleuser.networkTools.image.name")
    network_tools_image_tag = get_config("singleuser.networkTools.image.tag")
    ip_block_container = client.V1Container(
        name="block-cloud-metadata",
        image=f"{network_tools_image_name}:{network_tools_image_tag}",
        command=[
            "iptables",
            "-A",
            "OUTPUT",
            "-d",
            cloud_metadata.get("ip", "169.254.169.254"),
            "-j",
            "DROP",
        ],
        security_context=client.V1SecurityContext(
            privileged=True,
            run_as_user=0,
            capabilities=client.V1Capabilities(add=["NET_ADMIN"]),
        ),
    )

    c.KubeSpawner.init_containers.append(ip_block_container)


if get_config("debug.enabled", False):
    c.JupyterHub.log_level = "DEBUG"
    c.Spawner.debug = True

# load /usr/local/etc/jupyterhub/jupyterhub_config.d config files
config_dir = "/usr/local/etc/jupyterhub/jupyterhub_config.d"
if os.path.isdir(config_dir):
    for file_path in sorted(glob.glob(f"{config_dir}/*.py")):
        file_name = os.path.basename(file_path)
        print(f"Loading {config_dir} config: {file_name}")
        with open(file_path) as f:
            file_content = f.read()
        # compiling makes debugging easier: https://stackoverflow.com/a/437857
        exec(compile(source=file_content, filename=file_name, mode="exec"))

# load potentially seeded secrets
#
# NOTE: ConfigurableHTTPProxy.auth_token is set through an environment variable
#       that is set using the chart managed secret.
c.JupyterHub.cookie_secret = get_secret_value("hub.config.JupyterHub.cookie_secret")
# NOTE: CryptKeeper.keys should be a list of strings, but we have encoded as a
#       single string joined with ; in the k8s Secret.
#
c.CryptKeeper.keys = get_secret_value("hub.config.CryptKeeper.keys").split(";")

# load hub.config values, except potentially seeded secrets already loaded
for app, cfg in get_config("hub.config", {}).items():
    if app == "JupyterHub":
        cfg.pop("proxy_auth_token", None)
        cfg.pop("cookie_secret", None)
        cfg.pop("services", None)
    elif app == "ConfigurableHTTPProxy":
        cfg.pop("auth_token", None)
    elif app == "CryptKeeper":
        cfg.pop("keys", None)
    c[app].update(cfg)

# execute hub.extraConfig entries
for key, config_py in sorted(get_config("hub.extraConfig", {}).items()):
    print("Loading extra config: %s" % key)
    exec(config_py)
