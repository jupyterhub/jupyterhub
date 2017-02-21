"""autodoc extension for configurable traits"""

from traitlets import TraitType, Undefined
from sphinx.domains.python import PyClassmember
from sphinx.ext.autodoc import ClassDocumenter, AttributeDocumenter


class ConfigurableDocumenter(ClassDocumenter):
    """Specialized Documenter subclass for traits with config=True"""
    objtype = 'configurable'
    directivetype = 'class'

    def get_object_members(self, want_all):
        """Add traits with .tag(config=True) to members list"""
        check, members = super().get_object_members(want_all)
        get_traits = self.object.class_own_traits if self.options.inherited_members \
                     else self.object.class_traits
        trait_members = []
        for name, trait in sorted(get_traits(config=True).items()):
            # put help in __doc__ where autodoc will look for it
            trait.__doc__ = trait.help
            trait_members.append((name, trait))
        return check, trait_members + members


class TraitDocumenter(AttributeDocumenter):
    objtype = 'trait'
    directivetype = 'attribute'
    member_order = 1
    priority = 100

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, TraitType)

    def format_name(self):
        return 'config c.' + super().format_name()

    def add_directive_header(self, sig):
        default = self.object.get_default_value()
        if default is Undefined:
            default_s = ''
        else:
            default_s = repr(default)
        sig = ' = {}({})'.format(
            self.object.__class__.__name__,
            default_s,
        )
        return super().add_directive_header(sig)


def setup(app):
    app.add_autodocumenter(ConfigurableDocumenter)
    app.add_autodocumenter(TraitDocumenter)
