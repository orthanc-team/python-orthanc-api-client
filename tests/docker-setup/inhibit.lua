function IncomingHttpRequestFilter(method, uri, ip, username, httpHeaders)
    if string.match(uri, '/instances/')then
        return false
    end
    return true
end