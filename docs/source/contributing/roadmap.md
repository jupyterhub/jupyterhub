# The JupyterHub roadmap

This roadmap collects "next steps" for JupyterHub. It is about creating a
shared understanding of the project's vision and direction amongst
the community of users, contributors, and maintainers.
The goal is to communicate priorities and upcoming release plans.
It is not a aimed at limiting contributions to what is listed here.


## Using the roadmap
### Sharing Feedback on the Roadmap

All of the community is encouraged to provide feedback as well as share new
ideas with the community. Please do so by submitting an issue. If you want to
have an informal conversation first use one of the other communication channels.
After submitting the issue, others from the community will probably
respond with questions or comments they have to clarify the issue. The
maintainers will help identify what a good next step is for the issue.

### What do we mean by "next step"?

When submitting an issue, think about what "next step" category best describes
your issue:

* **now**, concrete/actionable step that is ready for someone to start work on.
These might be items that have a link to an issue or more abstract like
"decrease typos and dead links in the documentation"
* **soon**, less concrete/actionable step that is going to happen soon,
discussions around the topic are coming close to an end at which point it can
move into the "now" category
* **later**, abstract ideas or tasks, need a lot of discussion or
experimentation to shape the idea so that it can be executed. Can also
contain concrete/actionable steps that have been postponed on purpose
(these are steps that could be in "now" but the decision was taken to work on
them later)

### Reviewing and Updating the Roadmap

The roadmap will get updated as time passes (next review by 1st December) based
on discussions and ideas captured as issues.
This means this list should not be exhaustive, it should only represent
the "top of the stack" of ideas. It should
not function as a wish list, collection of feature requests or todo list.
For those please create a
[new issue](https://github.com/jupyterhub/jupyterhub/issues/new).

The roadmap should give the reader an idea of what is happening next, what needs
input and discussion before it can happen and what has been postponed.


## The roadmap proper
### Project vision

JupyterHub is a dependable tool used by humans that reduces the complexity of
creating the environment in which a piece of software can be executed.

### Now

These "Now" items are considered active areas of focus for the project:

* HubShare - a sharing service for use with JupyterHub.
    * Users should be able to:
        - Push a project to other users.
        - Get a checkout of a project from other users.
        - Push updates to a published project.
        - Pull updates from a published project.
        - Manage conflicts/merges by simply picking a version (our/theirs)
        - Get a checkout of a project from the internet. These steps are completely different from saving notebooks/files.
        - Have directories that are managed by git completely separately from our stuff.
        - Look at pushed content that they have access to without an explicit pull.
        - Define and manage teams of users.
            - Adding/removing a user to/from a team gives/removes them access to all projects that team has access to.
        - Build other services, such as static HTML publishing and dashboarding on top of these things.


### Soon

These "Soon" items are under discussion. Once an item reaches the point of an
actionable plan, the item will be moved to the "Now" section. Typically,
these will be moved at a future review of the roadmap.

* resource monitoring and management:
    - (prometheus?) API for resource monitoring
    - tracking activity on single-user servers instead of the proxy
    - notes and activity tracking per API token


### Later

The "Later" items are things that are at the back of the project's mind. At this
time there is no active plan for an item. The project would like to find the
resources and time to discuss these ideas.

- real-time collaboration
    - Enter into real-time collaboration mode for a project that starts a shared execution context.
    - Once the single-user notebook package supports realtime collaboration,
      implement sharing mechanism integrated into the Hub.
