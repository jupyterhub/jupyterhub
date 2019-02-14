=====
Users
=====

Module: :mod:`jupyterhub.user`
==============================

.. automodule:: jupyterhub.user

.. currentmodule:: jupyterhub.user

:class:`UserDict`
-----------------

.. autoclass:: UserDict
    :members:


:class:`User`
-------------

.. autoclass:: User
    :members: escaped_name
    
    .. attribute:: name
    
      The user's name
    
    .. attribute:: server
    
        The user's Server data object if running, None otherwise.
        Has ``ip``, ``port`` attributes.

    .. attribute:: spawner
    
        The user's :class:`~.Spawner` instance.
