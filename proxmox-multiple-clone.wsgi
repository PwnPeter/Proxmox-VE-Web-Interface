import logging
import sys

logging.basicConfig(stream=sys.stderr)


sys.path.insert(0, '/home/username/ExampleFlask/')


from proxmox-multiple-clone import app as application



application.secret_key = 'jksfd$*^^$*ù!fsfshjkhfgks'