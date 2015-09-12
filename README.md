# FileBackupApp

##Purpose:

Developed for an assignment at the Tech Academy Portland.  The idea is to create an application that will 
examine the contents of folders and copy contents that have changed to another folder on an interval.  

##How I'm doing it:

In my approach, I'm using the MVC architecture to structure the app.  

As such, there are three components:

- FileBackupUtilServer.py
-- This will run as a service on a windows machine.  It will run an event loop that does the periodic checking of folders and will respond to client RPC calls
- FileBackupUtilClient.py
-- This is a front-end application built using wxPython GUI framework.  It connects to the PyroService object in the service and makes remote calls to add new, update or delete jobs.
- filehist.db
-- A sqlite3 database that stores job information and a snapshot of the file timestamps in each folder
