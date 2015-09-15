__author__ = "Cody Landry"
"""
A Background application for performing
scheduled backups of new files in user-specified
locations.
"""
import schedule
import sqlite3
import pickle
import datetime as dt
import socket
import select
import sys
import Pyro4.core
import Pyro4.naming
import dirsync
import time
from collections import namedtuple


class PyroService():
    def __init__(self):
        self.db = None
        self.dbconn = None
        self.connect_to_db()
        self.schedule = schedule.Scheduler()

    def job_last_run(self, job):
        def format_time(t):
            return t.strftime('%Y-%m-%d %H:%M:%S') if t else '[never]'

        return '(last run: %s, next run: %s)' % (
                    format_time(job.last_run), format_time(job.next_run))

    def job_desc(self, job):
        if job.at_time is not None:
            return 'Every %s %s at %s' % (job.interval, job.unit[:-1] if job.interval == 1 else job.unit, job.at_time)
        else:
            return 'Every %s %s' % (job.interval, job.unit[:-1] if job.interval == 1 else job.unit)

    def connect_to_db(self):
        global dbconn, db
        try:
            self.db.close()
            self.db = None
            self.dbconn = None
        except:
            pass
        self.dbconn = sqlite3.connect('filehist.db')
        self.db = self.dbconn.cursor()
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs ('
                        'job_id INTEGER PRIMARY KEY AUTOINCREMENT ,'
                        'job INTEGER NOT NULL,'
                        'from_location TEXT NOT NULL,'
                        'to_location TEXT NOT NULL,'
                        'last_backup TEXT)')
        time.sleep(.5)
        self.dbconn.commit()

    def reload_tasks_from_db(self):
        # Gets all jobs
        self.connect_to_db()
        self.db.execute('SELECT * FROM jobs')
        jobs = []
        for row in list(self.db.fetchall()):
            job = pickle.loads(row[1])
            print self.job_desc(job)
            job.do(self.run_task, row[2], row[3])
            jobs.append(job)
        self.schedule.jobs = jobs

    def get_jobs(self):
        Job = namedtuple("Job", ('job_id', 'job_desc', 'from_location', 'to_location', 'last_backup', 'tableindex'))
        self.connect_to_db()
        self.db.execute('SELECT job_id, job, from_location, to_location, last_backup FROM jobs')
        ret = []
        for idx, row in enumerate(list(self.db.fetchall())):
            row = list(row)
            row[1] = self.job_desc(pickle.loads(row[1]))
            row.append(idx)
            ret.append(Job(*row))
        return ret

    @Pyro4.expose
    def update_job(self, job_id, job, from_location, to_location):
        self.connect_to_db()
        job_obj = pickle.loads(job)
        job_obj.do(self.run_task, from_location, to_location)
        self.db.execute('UPDATE jobs SET job = "{}", from_location = "{}", to_location = "{}" '
                        'WHERE job_id == {}'.format(job, from_location, to_location, job_id))
        self.dbconn.commit()
        self.reload_tasks_from_db()
        time.sleep(2)
        self.update_job()

    @Pyro4.oneway
    @Pyro4.expose
    def create_new_job(self, job, from_location, to_location):
        self.connect_to_db()
        job_obj = pickle.loads(job)
        job_obj.do(self.run_task, from_location, to_location)
        print self.job_desc(job_obj)
        print from_location, to_location
        self.db.execute('INSERT INTO jobs (job, from_location, to_location)'
                        'VALUES ("{}", "{}", "{}")'.format(job, from_location, to_location))
        self.dbconn.commit()
        self.reload_tasks_from_db()

    def delete_job(self, job_id):
        self.connect_to_db()
        self.db.execute('DELETE FROM jobs WHERE job_id == {}'.format(job_id))
        self.dbconn.commit()
        self.reload_tasks_from_db()

    def run_task(self, from_location, to_location):
        self.connect_to_db()
        timestamp = dt.datetime.now()
        self.db.execute('UPDATE jobs SET last_backup = "{}" '
                        'WHERE from_location == "{}" AND to_location == "{}"'.format(timestamp,
                                                                                     from_location, to_location))
        self.dbconn.commit()
        dirsync.sync(from_location, to_location, action='sync', verbose=True)

pyro_service = PyroService()
pyro_service.connect_to_db()
pyro_service.reload_tasks_from_db()


# <editor-fold desc="Pyro Server Setup">
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
serveruri=pyrodaemon.register(pyro_service)
print("server uri=%s" % serveruri)

# register it with the embedded nameserver directly
nameserverDaemon.nameserver.register("pyro_service", serveruri)

print("")
# </editor-fold>

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

    pyro_service.schedule.run_pending()


nameserverDaemon.close()
broadcastServer.close()
pyrodaemon.close()
print("done")
