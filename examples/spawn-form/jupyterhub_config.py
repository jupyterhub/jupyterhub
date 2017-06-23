"""
Example JupyterHub config allowing users to specify environment variables and notebook-server args
"""
import shlex

from jupyterhub.spawner import LocalProcessSpawner

class DemoFormSpawner(LocalProcessSpawner):
    def _options_form_default(self):
        default_env = "YOURNAME=%s\n" % self.user.name
        return """
        <label for="args">Extra notebook CLI arguments</label>
        <input name="args" placeholder="e.g. --debug"></input>
        <label for="env">Environment variables (one per line)</label>
        <textarea name="env">{env}</textarea>
        """.format(env=default_env)
    
    def options_from_form(self, formdata):
        options = {}
        options['env'] = env = {}
        
        env_lines = formdata.get('env', [''])
        for line in env_lines[0].splitlines():
            if line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
        
        arg_s = formdata.get('args', [''])[0].strip()
        if arg_s:
            options['argv'] = shlex.split(arg_s)
        return options
    
    def get_args(self):
        """Return arguments to pass to the notebook server"""
        argv = super().get_args()
        if self.user_options.get('argv'):
            argv.extend(self.user_options['argv'])
        return argv
    
    def get_env(self):
        env = super().get_env()
        if self.user_options.get('env'):
            env.update(self.user_options['env'])
        return env

c.JupyterHub.spawner_class = DemoFormSpawner
