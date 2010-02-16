import httplib, urllib2

from disco.error import CommError

FILE_BUFFER_SIZE = 10 * 1024**2
MAX_RETRIES = 10
http_pool = {}

def download(url, data = None, redir = False, offset = 0, method = None):
    if redir:
        req = urllib2.Request(url, data)
        if offset:
            req.add_header("Range", "bytes=%d-" % offset)
        try:
            c = urllib2.urlopen(req)
        except urllib2.HTTPError, x:
            raise CommError(x.msg, url)
        r = c.read()
        c.close()
        return r
    fd, sze, url = open_remote(url, data = data,
        offset = offset, method = method)
    return fd.read()


def check_code(fd, expected, url):
    if fd.status != expected:
        raise CommError("Invalid HTTP reply (expected %s got %s)" %\
                (expected, fd.status), url, fd.status)

def open_remote(url, data = None, expect = 200, offset = 0,
        ttl = MAX_RETRIES, method = None):
    http = None
    try:
        ext_host, ext_file = url[7:].split("/", 1)
        ext_file = "/" + ext_file

        # We can't open a new HTTP connection for each intermediate
        # result -- this would result to M * R TCP connections where
        # M is the number of maps and R the number of reduces. Instead,
        # we pool connections and reuse them whenever possible. HTTP
        # 1.1 defaults to keep-alive anyway.
        if ext_host in http_pool:
            http = http_pool[ext_host]
            if http._HTTPConnection__response:
                http._HTTPConnection__response.read()
        else:
            http = httplib.HTTPConnection(ext_host)
            http_pool[ext_host] = http

        h = {}
        if offset:
            h = {"Range": "bytes=%d-" % offset}
            expect = 206

        if data:
            meth = "POST"
        elif method != None:
            meth = method
        else:
            meth = "GET"
        
        http.request(meth, ext_file, data, headers = h)
        fd = http.getresponse()
        check_code(fd, expect, url)
        sze = fd.getheader("content-length")
        if sze:
            sze = int(sze)
        return (fd, sze, url)
    except (httplib.HTTPException, httplib.socket.error), e:
        if not ttl:
            raise CommError("Downloading %s failed "
                    "after %d attempts: %s" %
                    (url, MAX_RETRIES, e), url)
        if http:
            http.close()
        if ext_host in http_pool:
            del http_pool[ext_host]
        return open_remote(url, data, ttl=ttl - 1)

def upload(fname, urls, retries = 10):
    raise CommError("Uploading with httplib is not currently supported. Install pycurl.", urls[0])
