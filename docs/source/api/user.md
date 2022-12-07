# Users

## Module: {mod}`jupyterhub.user`

```{eval-rst}
.. automodule:: jupyterhub.user
```

### {class}`UserDict`

```{eval-rst}
.. autoclass:: UserDict
   :members:
```

### {class}`User`

```{eval-rst}
.. autoclass:: User
   :members: escaped_name

   .. attribute:: name

      The user's name

   .. attribute:: server

      The user's Server data object if running, None otherwise.
      Has ``ip``, ``port`` attributes.

   .. attribute:: spawner

      The user's :class:`~.Spawner` instance.
```
