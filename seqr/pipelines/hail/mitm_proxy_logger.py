"""
Plugin for mitmdump (https://mitmproxy.org/) that prints request and response headers.
This is useful for debugging connection or other network problems between 2 components
such as spark and a database.

mitmdump -q -v -s mitm_proxy_print_headers.py -R http://localhost:9200 -p 30001
""" 

from pprint import pprint

def response(flow):
    print("")
    print("="*50)
    #print("FOR: " + flow.request.url)
    print(flow.request.method + " " + flow.request.path + " " + flow.request.http_version)

    print("-"*50 + "request headers:")
    for k, v in flow.request.headers.items():
        print("%-20s: %s" % (k.upper(), v))
    pprint(flow.request.data.__dict__)

    print("-"*50 + "response headers:")
    for k, v in flow.response.headers.items():
        print("%-20s: %s" % (k.upper(), v))
    pprint(flow.response.data.__dict__)
