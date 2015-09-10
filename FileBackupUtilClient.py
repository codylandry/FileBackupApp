# Echo client program
from __future__ import print_function
import Pyro4

# saved as greeting-client.py


service = Pyro4.core.Proxy("PYRONAME:service")    # use name server object lookup uri shortcut

print(service.create_new_job(60, '/Users/codylandry/PycharmProjects/FileBackupApp/from_dir',
                             '/Users/codylandry/PycharmProjects/FileBackupApp/to_dir'))