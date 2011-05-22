from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from eulcommon.djangoextras.http.responses import HttpResponseSeeOtherRedirect
from eullocal.django.emory_ldap.backends import EmoryLDAPBackend

@permission_required('emory_ldap.add_emoryldapuserprofile')
def add_username(request):
    netid = request.POST['netid']
    backend = EmoryLDAPBackend()
    user_dn, user = backend.find_user(netid)
    if not user_dn:
        messages.add_message(request, messages.ERROR, 'No such user: ' + netid)

    location = reverse('admin:emory_ldap_emoryldapuserprofile_changelist')
    return HttpResponseSeeOtherRedirect(location)

