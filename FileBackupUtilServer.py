__author__ = "Cody Landry"
"""
A Background application for performing
scheduled backups of new files in user-specified
locations.
"""
from collections import namedtuple
import sqlite3
import os
import time
import shutil
import socket
import select
import sys
import Pyro4.core
import Pyro4.naming


Job = namedtuple('Job', ['job_id', 'interval', 'from_location', 'to_location', 'state'])


class PyroService():
    def __init__(self):
        self.db = None
        self.dbconn = None
        self.jobs = []
        self.connect_to_db()
        self.get_db_jobs()

    def connect_to_db(self):
        global dbconn, db
        try:
            self.db.close()
        except:
            pass
        self.dbconn = sqlite3.connect('filehist.db')
        self.db = self.dbconn.cursor()
        self.db.execute('CREATE TABLE IF NOT EXISTS FileHistory ('
                        'job_id INTEGER PRIMARY KEY AUTOINCREMENT ,'
                        'interval INTEGER NOT NULL,'
                        'from_location TEXT NOT NULL,'
                        'to_location TEXT NOT NULL,'
                        'state BLOB NOT NULL)')

    @staticmethod
    def get_dir_timestamps(directory):
        # Returns a dictionary of filename, timestamp pairs from the directory given
        hist = dict()
        for file in os.listdir(directory):
            hist[file] = os.path.getmtime(directory + '/' + file)
        return hist

    def get_db_jobs(self):
        # Gets all jobs
        self.connect_to_db()
        self.db.execute('SELECT * FROM FileHistory')
        for job in self.db.fetchall():
            self.jobs.append(Job(*job))

    def get_db_job(self, job_id):
        if self.jobs:
            for job in self.jobs:
                if job.job_id == job_id:
                    return job

    @Pyro4.expose
    def update_job(self, **kwargs):
        self.connect_to_db()

    @Pyro4.expose
    def create_new_job(self, interval, from_location, to_location):
        self.connect_to_db()
        state = self.get_dir_timestamps(from_location)
        try:
            self.db.execute('INSERT INTO filehistory (interval, from_location, to_location, state)'
                            'VALUES ("{}", "{}", "{}", "{}")'.format(interval, from_location, to_location, state))
            self.dbconn.commit()
            self.get_db_jobs()

            return True
        except Exception as e:
            print 'Exception in Function: create_new_job;', e
            return False

    def get_files_to_backup(self, job):
        files_to_backup = []
        current_state = self.get_dir_timestamps(job.from_location)
        try:
            # loop through each file in the job
            for file, timestamp in current_state.items():
                # get the modified times of each file in the 'to_location' directory
                to_location_state = self.get_dir_timestamps(job.to_location)
                # if the modified times aren't equal and it's been more than the interval period, backup the file
                if (current_state[file] != to_location_state.get(file, -1)) and \
                        (time.time() > current_state[file] + job.interval) and \
                        (os.path.isdir('/'.join([job.from_location, file])) is False):
                    files_to_backup.append(file)
            return files_to_backup
        except Exception as e:
            # User may delete files from the 'to location'
            print 'Exception in get_files_to_backup:', e
            return None

    def backup_file(self, job, file):
        # shutil copies the file and most of the metadata including the modified time
        from_path = '/'.join([job.from_location, file])
        to_path = '/'.join([job.to_location, file])

        if not os.path.isdir(from_path):
            shutil.copy2(from_path, to_path)
            print 'Backed Up File:', file, 'to:', job.to_location

    def update_dir_state(self, job):
        # Update the database 'state' of the 'from_location' for display to the user
        self.connect_to_db()
        self.db.execute('UPDATE FileHistory '
                        'SET state = "{}" WHERE job_id == "{}"'.format(self.get_dir_timestamps(job.from_location), job.job_id))
        self.dbconn.commit()

    def run_jobs(self):
        update = False
        for job in self.jobs:
            files = self.get_files_to_backup(job)
            if files:
                for f in files:
                    update = True
                    self.backup_file(job, f)
                if update:
                    self.update_dir_state(job)
                    update = False

    def backup_now(self, job_id):
        # Initiates a backup of all files
        globals()
        self.get_db_jobs()
        job = self.get_db_job(job_id)
        for f in eval(job.state).keys():
            self.backup_file(job, f)
        self.connect_to_db()
        self.update_dir_state(job)


service = PyroService()
service.connect_to_db()
service.run_jobs()

if sys.version_info < (3,0):
    input = raw_input

print("Make sure that you don't have a name server running already.")

Pyro4.config.SERVERTYPE = "multiplex"
hostname = socket.gethostname()

print("initializing services... servertype=%s" % Pyro4.config.SERVERTYPE)
# start a name server with broadcast server as well
nameserverUri, nameserverDaemon, broadcastServer = Pyro4.naming.startNS(host=hostname)
assert broadcastServer is not None, "expect a broadcast server to be created"

print("got a Nameserver, uri=%s" % nameserverUri)
print("ns daemon location string=%s" % nameserverDaemon.locationStr)
print("ns daemon sockets=%s" % nameserverDaemon.sockets)
print("bc server socket=%s (fileno %d)" % (broadcastServer.sock, broadcastServer.fileno()))

# create a Pyro daemon
pyrodaemon=Pyro4.core.Daemon(host=hostname)
print("daemon location string=%s" % pyrodaemon.locationStr)
print("daemon sockets=%s" % pyrodaemon.sockets)

# register a server object with the daemon
serveruri=pyrodaemon.register(service)
print("server uri=%s" % serveruri)

# register it with the embedded nameserver directly
nameserverDaemon.nameserver.register("service", serveruri)

print("")

while True:
    # create sets of the socket objects we will be waiting on
    # (a set provides fast lookup compared to a list)
    nameserverSockets = set(nameserverDaemon.sockets)
    pyroSockets = set(pyrodaemon.sockets)
    rs = [broadcastServer]  # only the broadcast server is directly usable as a select() object
    rs.extend(nameserverSockets)
    rs.extend(pyroSockets)
    rs, _, _ = select.select(rs, [], [], 3)
    eventsForNameserver = []
    eventsForDaemon = []
    for s in rs:
        if s is broadcastServer:
            print("Broadcast server received a request")
            broadcastServer.processRequest()
        elif s in nameserverSockets:
            eventsForNameserver.append(s)
        elif s in pyroSockets:
            eventsForDaemon.append(s)
    if eventsForNameserver:
        print("Nameserver received a request")
        nameserverDaemon.events(eventsForNameserver)
    if eventsForDaemon:
        print("Daemon received a request")
        pyrodaemon.events(eventsForDaemon)

    service.run_jobs()


nameserverDaemon.close()
broadcastServer.close()
pyrodaemon.close()
print("done")
