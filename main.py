from discord.ext import commands
from settings import *
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        # self.send_response(200)
        # self.send_header("Content-type", "text/html")
        # self.end_headers()
        # self.wfile.write(bytes("<html><head><title>https://pythonbasics.org</title></head>", "utf-8"))
        # self.wfile.write(bytes("<body>", "utf-8"))
        # self.wfile.write(bytes("<p>This is an example web server.</p>", "utf-8"))
        # self.wfile.write(bytes("</body></html>", "utf-8"))
        bot = commands.Bot(command_prefix="!")

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                bot.load_extension(f'cogs.{filename[:-3]}')
        
        bot.run(DISCORD_API_KEY)



server_object = HTTPServer(('', os.getenv("PORT", 3000)), MyServer)
server_object.serve_forever()