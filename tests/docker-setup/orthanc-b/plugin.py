import orthanc

TOKEN = orthanc.GenerateRestApiAuthorizationToken()

def GetApiToken(output, uri, **request):
    # unsafe !!!!  don't expose the token on a Rest API !!!! (don't run this experiment at home !)
    output.AnswerBuffer(TOKEN, 'text/plain')

orthanc.RegisterRestCallback('/api-token', GetApiToken)
