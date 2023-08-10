from docker import APIClient
from docker.tls import TLSConfig
from docker.utils import kwargs_from_env
from dockerspawner import DockerSpawner
from jupyterhub.auth import DummyAuthenticator
from traitlets import Dict

tls_config_by_host = {
    'a.example.com': {
        'base_url': 'https://a.example.com:2376',
        'tls_config': {
            'ca_cert': '/certs/a.example.com/ca.pem',
            'client_cert': ('/certs/a.example.com/cert.pem',
                            '/certs/a.example.com/key.pem',)
        }
    },
    'b.example.com': {
        'base_url': 'tcp://b.example.com:2375'
    },
    'c.example.com': {
        'base_url': 'https://c.example.com:2376',
        'tls_config': {
            'ca_cert': '/certs/c.example.com/ca.pem',
            'client_cert': ('/certs/c.example.com/cert.pem',
                            '/certs/c.example.com/key.pem',),
            'assert_hostname': False,
            'verify': False
        }
    }
}


class MultiHostDockerSpawner(DockerSpawner):
    tls_config_by_host = Dict(
        config=True,
        help="""See docker.client.TLSConfig constructor for options.""",
    )

    def _options_form_default(self):
        return """
        <div class="form-group">
            <label for="docker_host">Docker Host</label>
            <select name="docker_host" size="1" style="width: 100%;">
                <option value="a.example.com">a.example.com</option>
                <option value="b.example.com">b.example.com</option>
                <option value="c.example.com">c.example.com</option>
            </select>
        </div>
        """

    def options_from_form(self, formdata):
        docker_hosts = formdata.get("docker_host")
        if docker_hosts and docker_hosts[0]:
            docker_host = self.tls_config_by_host[docker_hosts[0].strip()]
            self.client_kwargs = {'base_url': docker_host['base_url']}
            return {'docker_host_base_url': docker_host['base_url']}

    @property
    def client(self):
        tls_config = [v['tls_config'] for _, v in self.tls_config_by_host.items()
                      if v['base_url'] == self.client_kwargs.get('base_url') and 'tls_config' in v]
        kwargs = {"version": "auto"}
        if tls_config:
            kwargs["tls"] = TLSConfig(**tls_config[0])
        kwargs.update(kwargs_from_env())
        kwargs.update(self.client_kwargs)
        return APIClient(**kwargs)


c = get_config()

c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.hub_connect_ip = '192.168.0.10' # Your jupyterhub public ip here.
                                             # It is used in nb container.
c.JupyterHub.authenticator_class = DummyAuthenticator
c.JupyterHub.spawner_class = MultiHostDockerSpawner

c.DockerSpawner.use_internal_ip = False
c.DockerSpawner.host_ip = '0.0.0.0'
c.DockerSpawner.tls_config_by_host = tls_config_by_host
c.DockerSpawner.remove = True
