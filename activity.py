#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2007-8 One Laptop per Child Association, Inc.
# Written by C. Scott Ananian <cscott@laptop.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Pango
from gi.repository import Vte

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityButton
from sugar3.activity.widgets import TitleEntry
from sugar3.activity.widgets import StopButton
from sugar3.activity import activityfactory
from sugar3.activity import activity
from sugar3.activity.activity import get_bundle_name
from sugar3.activity.activity import get_bundle_path
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3 import profile
from sugar3.datastore import datastore

import sys
import os
import os.path
from gettext import gettext as _


class ViewSourceActivity(activity.Activity):
    """Activity subclass which handles the 'view source' key."""

    def __init__(self, handle, **kwargs):
        super(ViewSourceActivity, self).__init__(handle, **kwargs)
        self.__source_object_id = None  # XXX: persist this across invocations?
        self.connect('key-press-event', self._key_press_cb)

    def _key_press_cb(self, widget, event):
        if Gdk.keyval_name(event.keyval) == 'XF86Start':
            self.view_source()
            return True
        return False

    def view_source(self):
        """Implement the 'view source' key by saving show.py to the
        datastore, and then telling the Journal to view it."""
        if self.__source_object_id is None:
            jobject = datastore.create()
            metadata = {
                'title': _('%s Source') % get_bundle_name(),
                'title_set_by_user': '1',
                'suggested_filename': 'show.py',
                'icon-color': profile.get_color().to_string(),
                'mime_type': 'text/x-python',
            }
            for k, v in metadata.items():
                jobject.metadata[k] = v  # dict.update method is missing =(
            jobject.file_path = os.path.join(get_bundle_path(), 'show.py')
            datastore.write(jobject)
            self.__source_object_id = jobject.object_id
            jobject.destroy()
        self.journal_show_object(self.__source_object_id)

TARGET_TYPE_TEXT = 80


class VteActivity(ViewSourceActivity):
    """Activity subclass built around the Vte terminal widget."""

    def __init__(self, handle):
        super(VteActivity, self).__init__(handle)
        toolbox = ToolbarBox()
        self.set_toolbar_box(toolbox)
        toolbox.show()

        self.max_participants = 1

        toolbar_box = ToolbarBox()

        activity_button = ActivityButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        title_entry = TitleEntry(self)
        toolbar_box.toolbar.insert(title_entry, -1)
        title_entry.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

        # creates vte widget
        self._vte = Vte.Terminal()
        self._vte.set_size(30, 5)
        self._vte.set_size_request(200, 300)
        font = 'Monospace 10'
        self._vte.set_font(Pango.FontDescription(font))
        self._vte.connect('selection-changed', self._on_selection_changed_cb)
        self._vte.drag_dest_set(Gtk.DestDefaults.ALL,
                                [],
                                Gdk.DragAction.COPY)
        self._vte.connect('drag_data_received', self._on_drop_cb)
        # ...and its scrollbar
        vtebox = Gtk.HBox()
        vtebox.pack_start(self._vte, True, True, 0)
        vtesb = Gtk.VScrollbar()
        vtesb.show()
        vtebox.pack_start(vtesb, False, False, 0)
        self.set_canvas(vtebox)
        self.show_all()
        # now start subprocess.
        self._vte.connect("child-exited", self.on_child_exit)
        self._vte.grab_focus()
        bundle_path = activity.get_bundle_path()
        # the 'sleep 1' works around a bug with the command dying before
        # the vte widget manages to snarf the last bits of its output
        self._pid = self._vte.spawn_sync(
            Vte.PtyFlags.DEFAULT, bundle_path,
            ['/bin/sh', '-c', 'python %s/show.py; sleep 1' % bundle_path],
            ["PYTHONPATH=%s/library" % bundle_path],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD, None, None)

    def _on_copy_clicked_cb(self, widget):
        if self._vte.get_has_selection():
            self._vte.copy_clipboard()

    def _on_paste_clicked_cb(self, widget):
        self._vte.paste_clipboard()

    def _on_selection_changed_cb(self, widget):
        self._copy_button.set_sensitive(self._vte.get_has_selection())

    def _on_drop_cb(self, widget, context, x, y, selection, targetType, time):
        if targetType == TARGET_TYPE_TEXT:
            self._vte.feed_child(selection.data)

    def on_child_exit(self, widget, status):
        sys.exit(0)


def _main():
    """Launch this activity from the command line."""
    ab = ActivityBundle(os.path.dirname(__file__) or '.')
    ai = ActivityInfo(name=ab.get_name(),
                      icon=None,
                      bundle_id=ab.get_bundle_id(),
                      version=ab.get_activity_version(),
                      path=ab.get_path(),
                      show_launcher=ab.get_show_launcher(),
                      command=ab.get_command(),
                      favorite=True,
                      installation_time=ab.get_installation_time(),
                      position_x=0, position_y=0)
    env = activityfactory.get_environment(ai)
    cmd_args = activityfactory.get_command(ai)
    os.execvpe(cmd_args[0], cmd_args, env)

if __name__ == '__main__':
    _main()
