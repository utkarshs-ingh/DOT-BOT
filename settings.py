import os
import socket

DEBUG = os.getenv("DEBUG", False)
sock = socket.socket() 
port = int(os.environ.get('PORT', 17995)) or 3000

if DEBUG:
    print("Debug Mode")
    from pathlib import Path
    from dotenv import load_dotenv
    env_path = Path(".") / ".env.debug"
    load_dotenv(dotenv_path = env_path)
    from settings_files.development import *
else:
    print("Production Mode")
    from pathlib import Path
    from dotenv import load_dotenv
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path = env_path)
    sock.bind(('', port))     
    from settings_files.production import *