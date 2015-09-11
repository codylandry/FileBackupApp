# Echo client program
from __future__ import print_function
import Pyro4
import wx

# TODO: Make this a class property
service = Pyro4.core.Proxy("PYRONAME:service")    # use name server object lookup uri shortcut


class WindowClass(wx.Frame):
    """
    Skeleton code for gui
    """
    def __init__(self, *args, **kwargs):
        super(WindowClass, self).__init__(*args, **kwargs)

        self.Centre()
        self.SetTitle('File Backup App')

        # TODO: Add basic gui elements to CRUD 'jobs' and view status of backups
        # TODO: Add table to view the sqlite db contents

        # --------------Panel Setup-----------------------------
        panel = wx.Panel(self)

        self.Show()


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


