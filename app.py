import http.server, socketserver
PORT=8080
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**k): super().__init__(*a,directory='.',**k)
print(f"OSTO PRIVADO 8551 corriendo en {PORT}")
with socketserver.TCPServer(("0.0.0.0",PORT),H) as httpd:
    httpd.serve_forever()
