'''
Great parts of this code were copied and modified from this project(https://tildegit.org/solderpunk/gemini-demo-1).
I wouldnt have been able to do this without this resource. Thanks for the awsome code.
'''


import cgi
import mailcap
import os
import socket
import ssl
import tempfile
import textwrap
import urllib.parse
import pyotherside

storage_dir = "/home/phablet/.local/share/gem.aaron"

class Gemini:
    def __init__(self):
        self.makeDirs()
        # load position
        position_data = self.read_file("where_am_I.txt")
        self.position = int(position_data if position_data != None else '0')
        # Load history
        history_data = self.read_file("history.txt")
        self.history = history_data if history_data != None else []
        # Load future
        future_data = self.read_file("future.txt")
        self.future = future_data if future_data != None else []

    def read_file(self, filename):
        f = self.open_file(filename, "rb")

        if f == None:
            return None

        f_data = f.read()
        f.close()

        return f_data

    def save_data(self):
        position_file = self.open_file("where_am_I.txt", "wb")
        history_file = self.open_file("history.txt", "wb")

        position_file.write(str(self.position))
        history_file.write(','.join(self.history))

        position_file.close()
        history_file.close()

    def makeDirs(self):
        try:
            os.mkdir(storage_dir)
        except:
            pass

    def absolutise_url(self, base, relative):
        # Absolutise relative links
        if "://" not in relative:
            # Python's URL tools somehow only work with known schemes?
            base = base.replace("gemini://","http://")
            relative = urllib.parse.urljoin(base, relative)
            relative = relative.replace("http://", "gemini://")
        return relative

    def get_site(self, url):
        parsed_url = urllib.parse.urlparse(url)
        while True:
            s = socket.create_connection((parsed_url.netloc, 1965))
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            s = context.wrap_socket(s, server_hostname = parsed_url.netloc)
            s.sendall((url + '\r\n').encode("UTF-8"))
            # Get header and check for redirects
            fp = s.makefile("rb")
            header = fp.readline()
            header = header.decode("UTF-8").strip()
            status, mime = header.split()[:2]
            # Handle input requests
            if status.startswith("1"):
                # Prompt
                query = input("INPUT" + mime + "> ")
                url += "?" + urllib.parse.quote(query) # Bit lazy...
                # Follow redirects
            elif status.startswith("3"):
                url = self.absolutise_url(url, mime)
                parsed_url = urllib.parse.urlparse(url)
            # Otherwise, we're done.
            else:
                mime, mime_opts = cgi.parse_header(mime)
                body = fp.read()
                body = body.decode(mime_opts.get("charset","UTF-8"))
                return str(body)
                break

    def get_links(self, body, url):
        links = []
        for line in body.splitlines():
            if line.startswith("=>"):
                bits = line[2:].strip().split(maxsplit=1)
                link_url = bits[0]
                link_url = self.absolutise_url(url, link_url)
                links.append(link_url)
        return links



    def instert_html_links(self, body, links):
        mdBody = ""
        for line in body.splitlines():
            if "=>" in line:
                try:
                    line =  '<a style="color: #FFC0CB" href="'+links[0]+'">'+line+'</a>'
                    del links[0]
                    mdBody += line
                    mdBody += "<br>"
                    mdBody += "<br>"
                    #print("here")
                except:
                    mdBody += line
                    #print("err")
                    pass
            elif line.startswith("#"):
                if line.startswith("###"):
                    line = line.replace("###", "<h3>")
                    line += "</h3>"
                    mdBody += line
                elif line.startswith("##"):
                    line = line.replace("##", "<h2>")
                    line += "</h2>"
                    mdBody += line
                elif line.startswith("#"):
                    line = line.replace("#", "<h1>")
                    line += "</h1>"
                    mdBody += line
                else:
                    pass

            else:
                #print("nolink")
                mdBody += line + "\n"
                mdBody += "<br>"
                mdBody += "<br>"
        return mdBody

    def open_file(self, filename, mode="r+"):
        try:
            f = open(filename, mode) if os.path.exists(filename) else None
        except:
            file_path = "{}/{}".format(storage_dir, filename)
            f = open(file_path, mode) if os.path.exists(file_path) else None

        return f

    def top(self, stack):
        stack_size = len(stack)

        if stack_size == 0:
            return None

        return stack[stack_size - 1]

    def back(self):
        if len(self.history) == 1:
            return self.load(self.history[0])

        self.future.append(self.history.pop())
        url = self.top(self.history)
        print('back', self.history)

        return self.load(url)

    def goto(self, url):
        self.history.append(url)
        print('goto', self.history)

        return self.load(url)

    def load(self, url):
        pyotherside.send('loading', url)
        try:
            gemsite = self.get_site(url)
            gemsite = self.instert_html_links(gemsite, self.get_links(gemsite, url))

            pyotherside.send('onLoad', gemsite)
        except Exception as e:
            print("Error:", e.message)
            pyotherside.send('onLoad', "uhm... seems like this site does not exist, it might also be bug <br> ¯\_( ͡❛ ͜ʖ ͡❛)_/¯")

        return;

gemini = Gemini()
pyotherside.atexit(gemini.save_data)