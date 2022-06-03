c = get_config()  # noqa


options_form_tpl = """
<label for="image">Image</label>
<input name="image" class="form-control" placeholder="the image to launch (default: {default_image})"></input>
"""


def get_options_form(spawner):
    return options_form_tpl.format(default_image=spawner.image)


c.DockerSpawner.options_form = get_options_form

from dockerspawner import DockerSpawner


class CustomDockerSpawner(DockerSpawner):
    def options_from_form(self, formdata):
        options = {}
        image_form_list = formdata.get("image", [])
        if image_form_list and image_form_list[0]:
            options["image"] = image_form_list[0].strip()
            self.log.info(f"User selected image: {options['image']}")
        return options

    def load_user_options(self, options):
        image = options.get("image")
        if image:
            self.log.info(f"Loading image {image}")
            self.image = image


c.JupyterHub.spawner_class = CustomDockerSpawner

# the rest of the config is testing boilerplate
# to make the Hub connectable from the containers

# dummy for testing. Don't use this in production!
c.JupyterHub.authenticator_class = "dummy"
# while using dummy auth, make the *public* (proxy) interface private
c.JupyterHub.ip = "127.0.0.1"

# we need the hub to listen on all ips when it is in a container
c.JupyterHub.hub_ip = "0.0.0.0"

# may need to set hub_connect_ip to be connectable to containers
# default hostname behavior usually works, though
# c.JupyterHub.hub_connect_ip

# pick a default image to use when none is specified
c.DockerSpawner.image = "jupyter/base-notebook"

# delete containers when they stop
c.DockerSpawner.remove = True
