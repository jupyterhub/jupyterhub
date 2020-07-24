# Frequently asked questions


### How do I share links to notebooks?

In short, where you see `/user/name/notebooks/foo.ipynb` use `/hub/user-redirect/notebooks/foo.ipynb` (replace `/user/name` with `/hub/user-redirect`).

Sharing links to notebooks is a common activity,
and can look different based on what you mean.
Your first instinct might be to copy the URL you see in the browser,
e.g. `hub.jupyter.org/user/yourname/notebooks/coolthing.ipynb`.
However, let's break down what this URL means:

`hub.jupyter.org/user/yourname/` is the URL prefix handled by *your server*,
which means that sharing this URL is asking the person you share the link with
to come to *your server* and look at the exact same file.
In most circumstances, this is forbidden by permissions because the person you share with does not have access to your server.
What actually happens when someone visits this URL will depend on whether your server is running and other factors.

But what is our actual goal?
A typical situation is that you have some shared or common filesystem,
such that the same path corresponds to the same document
(either the exact same document or another copy of it).
Typically, what folks want when they do sharing like this
is for each visitor to open the same file *on their own server*,
so Breq would open `/user/breq/notebooks/foo.ipynb` and
Seivarden would open `/user/seivarden/notebooks/foo.ipynb`, etc.

JupyterHub has a special URL that does exactly this!
It's called `/hub/user-redirect/...` and after the visitor logs in,
So if you replace `/user/yourname` in your URL bar
with `/hub/user-redirect` any visitor should get the same
URL on their own server, rather than visiting yours.

In JupyterLab 2.0, this should also be the result of the "Copy Shareable Link"
action in the file browser.
