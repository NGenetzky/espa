import json
from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse

def as_json(payload):
    return json.dumps(payload)

def json_response(context, **response_kwargs):
        data = as_json(context)
        response_kwargs['content_type'] = 'application/json'
        return HttpResponse(data, **response_kwargs)

class APIView(View):
    as_http = True

class Versions(APIView):
    def get(self, request):
        d = {'versions': [
                {'version':1.0, 'url':reverse('api_v1_description')},
            ]}
        
        if self.as_http is False:
            return as_json(d)
        else:
            return json_response(d, {})


#SHIT.  How are you going to write testable code not dependant on an HTTP server?