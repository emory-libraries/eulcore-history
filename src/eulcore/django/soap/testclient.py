# file django\soap\testclient.py
# 
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from django.test.client import Client
from soaplib.client import SimpleSoapClient, _err_format
from soaplib.serializers.primitive import Fault
from soaplib.soap import from_soap, make_soap_envelope
from xml.etree import cElementTree as ElementTree

class DjangoSoapTestServiceClient:
    # copied from soaplib.ServiceClient
    def __init__(self, path, server_impl):        
        self.server = server_impl
        host = None     # expected by SimpleSoapClient init, but unused
        # FIXME: Seems like there should be a better way than copying all
        # the methods.
        for method in self.server.methods():
            setattr(self, method.name, DjangoSoapTestClient(host, path, method))


class DjangoSoapTestClient(SimpleSoapClient):
     def __call__(self,*args,**kwargs):
         # copied & simplified from soaplib.client.SimpleSoapClient
        if len(args) != len(self.descriptor.inMessage.params):
            argstring = '\r\n'.join([ '    ' + str(arg) for arg in args ])
            paramstring = '\r\n'.join([ '    ' + str(p[0]) for p in self.descriptor.inMessage.params ])
            err_msg = _err_format % (argstring, paramstring)
            raise Exception(err_msg)

        msg = self.descriptor.inMessage.to_xml(*args)

        # grab the soap headers passed into this call
        headers = kwargs.get('headers', [])
        msgid = kwargs.get('msgid')
        if msgid:
            # special case for the msgid field as a convenience
            # when dealing with async callback methods
            headers.append(create_relates_to_header(msgid))

        envelope = make_soap_envelope(msg, header_elements=headers)

        body = ElementTree.tostring(envelope)
        # removed http header logic - not needed for django test client

        # use django.test.client to send request
        client = Client()
        response = client.post(self.path, body, content_type="text/xml")
        data = response.content        
        
        if str(response.status_code) not in ('200', '202'):
            # consider everything NOT 200 or 202 as an error response
            
            if str(response.status_code) == '500': 
                fault = None
                try:
                    payload, headers = from_soap(data)
                    fault = Fault.from_xml(payload)
                except:
                    trace = StringIO()
                    import traceback
                    traceback.print_exc(file=trace)
                    
                    fault = Exception('Unable to read response \n  %s %s \n %s \n %s' % \
                            (response.status, response.reason, trace.getvalue(), data))
                raise fault
            else:
                raise Exception('%s %s' % (response.status,response.reason,))

        if not self.descriptor.outMessage.params:            
            return

        payload, headers = from_soap(data)        
        
        results = self.descriptor.outMessage.from_xml(payload)        
        return results[0]
