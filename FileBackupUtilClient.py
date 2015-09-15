# Echo client program
from __future__ import print_function
import Pyro4
import wx
import schedule
import pickle
from wx.lib.masked import TimeCtrl
from wx.grid import Grid
import time


def run_task(job):
    pass

class BackupConfig(wx.Frame):
    def __init__(self, parent, **kwargs):
        super(BackupConfig, self).__init__(parent, **kwargs)
        self.parent = parent
        self.Size = (640, 480)
        self.Centre()
        self.SetTitle('Select Backup Configuration')

        panel = wx.Panel(self)

        # Option 1: Back up on an interval

        self.backup_every_radiobtn = wx.RadioButton(panel, -1, "Backup every:", pos=(10, 44))
        self.backup_at_radiobtn = wx.RadioButton(panel, -1, "Backup at:", pos=(10, 82))
        self.backup_every_radiobtn.SetValue(True)

        self.multiplier = wx.SpinCtrl(panel, pos=(435, 42), size=(57, 24))
        self.multiplier.SetRange(1, 100)

        self.periodicity = wx.Choice(panel, -1, pos=(525, 40), size=(99, 24),
                                choices=['seconds', 'minutes', 'hours', 'days', 'weeks'])

        self.time_spin_btn = wx.SpinButton(panel, -1, style=wx.SP_VERTICAL, pos=(510, 79))
        self.time_ = TimeCtrl(panel, -1, pos=(408, 80), spinButton=self.time_spin_btn)

        self.day_of_week = wx.Choice(panel, -1, pos=(525, 77), size=(99, 24),
                                choices=['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'])

        submit = wx.Button(panel, -1, "Submit", pos=(10, 100))

        submit.Bind(wx.EVT_BUTTON, self.push_to_parent)

        self.Show()

    def push_to_parent(self, event):
        if self.backup_every_radiobtn.GetValue() == True:
            self.parent.create_new_job(type_='EVERY',
                                       multiplier=self.multiplier.GetValue(),
                                       periodicity=self.periodicity.GetString(self.periodicity.GetSelection()))
        elif self.backup_at_radiobtn.GetValue() == True:
            self.parent.create_new_job(type_='AT',
                                       time_=self.time_.GetValue(),
                                       day_of_week=self.day_of_week.GetString(self.day_of_week.GetSelection()))
        self.Close()


class WindowClass(wx.Frame):
    """
    Skeleton code for gui
    """
    def __init__(self, *args, **kwargs):
        super(WindowClass, self).__init__(*args, **kwargs)

        self.pyro_service = Pyro4.core.Proxy("PYRONAME:pyro_service")    # use name server object lookup uri shortcut


        self.Size = (640, 280)
        self.Centre()
        self.SetTitle('File Backup App')

        # TODO: Add basic gui elements to CRUD 'jobs' and view status of backups
        # TODO: Add table to view the sqlite db contents

        # --------------Panel Setup-----------------------------
        panel = wx.Panel(self)

        self.table = wx.ListCtrl(panel, -1, pos=(10, 10), size=(611, 199), style=wx.LC_REPORT | wx.LC_HRULES)
        self.update_table()

        newbtn = wx.Button(panel, -1, "New", pos=(10, 218), size=(65, 24))
        editbtn = wx.Button(panel, -1, "Edit", pos=(85, 218), size=(65, 24))
        deletebtn = wx.Button(panel, -1, "Delete", pos=(160, 218), size=(65, 24))

        newbtn.Bind(wx.EVT_BUTTON, self.newbtn_handler)

        self.Show()

    def update_table(self):
        columns = [
            ("Backup Type", 150),
            ("Source", 100),
            ("Destination", 100),
            ("Last Backup", 200)
        ]
        self.tablevalues = self.pyro_service.get_jobs()
        self.table.ClearAll()

        if len(self.tablevalues):
            for i, col in enumerate(columns):
                self.table.InsertColumn(i, col[0], width=col[1])
            for i, row in enumerate(self.tablevalues):
                edited_row = []
                for g, col in enumerate(row[1:]):
                    if g in [1, 2]:
                        edited_row.append(str(col)[col.rfind('/'):])
                    else:
                        edited_row.append(str(col))
                self.table.Append(edited_row)

    def show_dirdialog(self, message="Select Folder", defaultPath=""):
        dirdialog = wx.DirDialog(None, message, defaultPath=defaultPath)

        if dirdialog.ShowModal() == wx.ID_OK:
            return dirdialog.GetPath()

    def create_new_job(self, *args, **kwargs):
        newjobcall = None
        if kwargs['type_'] == 'EVERY':
            newjobcall = "schedule.Job(" + str(kwargs['multiplier']) + ")." + str(kwargs['periodicity'])
        elif kwargs['type_'] == 'AT':
            print(kwargs['time_'])
            newjobcall = "schedule.Job().at('" + str(kwargs['time_']) + "')"

        if newjobcall:
            new_job = eval(newjobcall)
            if kwargs['type_'] == 'AT':
                new_job.start_day = kwargs['day_of_week'].lower()
            new_job = pickle.dumps(new_job)
            self.pyro_service.create_new_job(new_job, self.temp_source, self.temp_target)
            time.sleep(2)
            self.update_table()


    def newbtn_handler(self, event):

        self.temp_source = self.show_dirdialog(message="Select Source Folder")
        if not self.temp_source:
            return
        time.sleep(1)
        self.temp_target = self.show_dirdialog(message="Select Target Folder", defaultPath=self.temp_source)
        if not self.temp_target:
            return

        BackupConfig(self)

        """
        interval = 5
        periodicity = 'seconds'

        test_job = "schedule.Job(" + str(interval) + ")." + periodicity
        test_job = pickle.dumps(eval(test_job))

        #test_job = pickle.dumps(schedule.Job(20).seconds)

        self.pyro_service.create_new_job(test_job, '/Users/codylandry/PycharmProjects/FileBackupApp/test/from_dir',
                                         '/Users/codylandry/PycharmProjects/FileBackupApp/test/to_dir')
        """


def main():
    """
    Instantiate the App and start the MainLoop
    :return:
    """
    app = wx.App()
    WindowClass(None)
    app.MainLoop()

if __name__ == "__main__":
    main()


