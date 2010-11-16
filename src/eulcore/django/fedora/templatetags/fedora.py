from django import template
from eulcore.fedora.util import RequestFailed, PermissionDenied

register = template.Library()

class CatchFedoraErrorsNode(template.Node):
    """Template render node for catching fedora access errors and providing
    fallback content."""
    def __init__(self, fedora_access, permission_denied=None,
                 fedora_failed=None):
        self.fedora_access = fedora_access
        self.permission_denied = permission_denied
        self.fedora_failed = fedora_failed

    def render(self, context):
        try:
            return self.fedora_access.render(context)
        except PermissionDenied:
            if self.permission_denied is not None:
                return self.permission_denied.render(context)
            elif self.fedora_failed is not None:
                return self.fedora_failed.render(context)
            else:
                return ''
        except RequestFailed:
            if self.fedora_failed is not None:
                return self.fedora_failed.render(context)
            else:
                return ''


@register.tag(name='fedora_access')
def do_catch_fedora_errors(parser, token):
    """Catches fedora errors between ``{% fedora_access %}`` and
    ``{% end_fedora_access %}``. Template designers may specify 
    optional ``{% permission_denied %}`` and ``{% fedora_failed %}``
    sections with fallback content in case of permission or other errors
    while rendering the main block.
    """

    END_TAGS = ('end_fedora_access',
                'permission_denied', 'fedora_failed')

    blocks = {}
    blocks['fedora_access'] = parser.parse(END_TAGS)
    token = parser.next_token()
    while token.contents != 'end_fedora_access':
        # need to convert token.contents manually to a str. django gives us
        # a unicode. we use it below in **blocks, but python 2.6.2 and
        # earlier can't use **kwargs with unicode keys. (2.6.5 is ok with
        # it; not sure about intervening versions.) in any case, direct
        # conversion to string is safe here (i.e., no encoding needed)
        # because the parser guarantees it's one of our END_TAGS, which are
        # all ascii.
        current_block = str(token.contents)
        if current_block in blocks:
            raise template.TemplateSyntaxError(
                current_block + ' may appear only once in a fedora_access block')

        blocks[current_block] = parser.parse(END_TAGS)
        token = parser.next_token()

    return CatchFedoraErrorsNode(**blocks)
