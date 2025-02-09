# This file is part of Gajim.
#
# Gajim is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation; version 3 only.
#
# Gajim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gajim.  If not, see <http://www.gnu.org/licenses/>.

'''
GUI classes related to plug-in management.

:author: Mateusz Biliński <mateusz@bilinski.it>
:since: 6th June 2008
:copyright: Copyright (2008) Mateusz Biliński <mateusz@bilinski.it>
:license: GPL
'''

import os
from enum import IntEnum
from enum import unique

from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import Gdk

from gajim.common import app
from gajim.common import configpaths
from gajim.common import ged
from gajim.common.exceptions import PluginsystemError
from gajim.common.helpers import open_uri
from gajim.common.nec import EventHelper

from gajim.plugins.helpers import GajimPluginActivateException
from gajim.plugins.plugins_i18n import _

from gajim.gtk.dialogs import WarningDialog
from gajim.gtk.dialogs import DialogButton
from gajim.gtk.dialogs import NewConfirmationDialog
from gajim.gtk.filechoosers import ArchiveChooserDialog
from gajim.gtk.util import get_builder
from gajim.gtk.util import load_icon


@unique
class Column(IntEnum):
    PLUGIN = 0
    NAME = 1
    ACTIVE = 2
    ACTIVATABLE = 3
    ICON = 4


class PluginsWindow(EventHelper):

    def __init__(self):
        EventHelper.__init__(self)

        builder = get_builder('plugins_window.ui')
        self.window = builder.get_object('plugins_window')
        self.window.set_transient_for(app.interface.roster.window)

        widgets_to_extract = ('plugins_notebook', 'plugin_name_label',
            'plugin_version_label', 'plugin_authors_label',
            'plugin_homepage_linkbutton', 'install_plugin_button',
            'uninstall_plugin_button', 'configure_plugin_button',
            'installed_plugins_treeview', 'available_text',
            'available_text_label')

        for widget_name in widgets_to_extract:
            setattr(self, widget_name, builder.get_object(widget_name))

        self.plugin_description_textview = builder.get_object('description')

        # Disable 'Install from ZIP' for Flatpak installs
        if app.is_flatpak():
            self.install_plugin_button.set_tooltip_text(
                _('Click to view Gajim\'s wiki page on how to install plugins in Flatpak.'))

        self.installed_plugins_model = Gtk.ListStore(object, str, bool, bool,
            GdkPixbuf.Pixbuf)
        self.installed_plugins_treeview.set_model(self.installed_plugins_model)

        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn(_('Plugin'))#, renderer, text=Column.NAME)
        cell = Gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.add_attribute(cell, 'pixbuf', Column.ICON)
        col.pack_start(renderer, True)
        col.add_attribute(renderer, 'text', Column.NAME)
        col.set_property('expand', True)
        self.installed_plugins_treeview.append_column(col)

        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.installed_plugins_toggled_cb)
        col = Gtk.TreeViewColumn(_('Active'), renderer, active=Column.ACTIVE,
            activatable=Column.ACTIVATABLE)
        self.installed_plugins_treeview.append_column(col)

        self.def_icon = load_icon('preferences-desktop',
                                  self.window,
                                  pixbuf=True)

        # connect signal for selection change
        selection = self.installed_plugins_treeview.get_selection()
        selection.connect('changed',
            self.installed_plugins_treeview_selection_changed)
        selection.set_mode(Gtk.SelectionMode.SINGLE)

        self._clear_installed_plugin_info()

        self.fill_installed_plugins_model()
        root_iter = self.installed_plugins_model.get_iter_first()
        if root_iter:
            selection.select_iter(root_iter)

        builder.connect_signals(self)

        self.plugins_notebook.set_current_page(0)

        # Adding GUI extension point for Plugins that want to hook the Plugin Window
        app.plugin_manager.gui_extension_point('plugin_window', self)

        self.register_events([
            ('plugin-removed', ged.GUI1, self._on_plugin_removed),
            ('plugin-added', ged.GUI1, self._on_plugin_added),
        ])

        self.window.show_all()

    def get_notebook(self):
        # Used by plugins
        return self.plugins_notebook

    def on_key_press_event(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.window.destroy()

    def installed_plugins_treeview_selection_changed(self, treeview_selection):
        model, iter_ = treeview_selection.get_selected()
        if iter_:
            plugin = model.get_value(iter_, Column.PLUGIN)
            self._display_installed_plugin_info(plugin)
        else:
            self._clear_installed_plugin_info()

    def _display_installed_plugin_info(self, plugin):
        self.plugin_name_label.set_text(plugin.name)
        self.plugin_version_label.set_text(plugin.version)
        self.plugin_authors_label.set_text(plugin.authors)
        markup = '<a href="%s">%s</a>' % (plugin.homepage, plugin.homepage)
        self.plugin_homepage_linkbutton.set_markup(markup)

        if plugin.available_text:
            text = _('Warning: %s') % plugin.available_text
            self.available_text_label.set_text(text)
            self.available_text.show()
            # Workaround for https://bugzilla.gnome.org/show_bug.cgi?id=710888
            self.available_text.queue_resize()
        else:
            self.available_text.hide()

        self.plugin_description_textview.set_text(plugin.description)

        self.uninstall_plugin_button.set_property(
            'sensitive', configpaths.get('PLUGINS_USER') in plugin.__path__)
        self.configure_plugin_button.set_property(
            'sensitive', plugin.config_dialog is not None)

    def _clear_installed_plugin_info(self):
        self.plugin_name_label.set_text('')
        self.plugin_version_label.set_text('')
        self.plugin_authors_label.set_text('')
        self.plugin_homepage_linkbutton.set_markup('')

        self.plugin_description_textview.set_text('')
        self.uninstall_plugin_button.set_property('sensitive', False)
        self.configure_plugin_button.set_property('sensitive', False)

    def fill_installed_plugins_model(self):
        pm = app.plugin_manager
        self.installed_plugins_model.clear()
        self.installed_plugins_model.set_sort_column_id(1, Gtk.SortType.ASCENDING)

        for plugin in pm.plugins:
            icon = self.get_plugin_icon(plugin)
            self.installed_plugins_model.append([plugin, plugin.name,
                plugin.active and plugin.activatable, plugin.activatable, icon])

    def get_plugin_icon(self, plugin):
        icon_file = os.path.join(plugin.__path__, os.path.split(
                plugin.__path__)[1]) + '.png'
        icon = self.def_icon
        if os.path.isfile(icon_file):
            icon = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_file, 16, 16)
        return icon

    def installed_plugins_toggled_cb(self, cell, path):
        is_active = self.installed_plugins_model[path][Column.ACTIVE]
        plugin = self.installed_plugins_model[path][Column.PLUGIN]

        if is_active:
            app.plugin_manager.deactivate_plugin(plugin)
        else:
            try:
                app.plugin_manager.activate_plugin(plugin)
            except GajimPluginActivateException as e:
                WarningDialog(_('Plugin failed'), str(e),
                    transient_for=self.window)
                return

        self.installed_plugins_model[path][Column.ACTIVE] = not is_active

    def on_plugins_window_destroy(self, widget):
        '''Close window'''
        self.unregister_events()
        app.plugin_manager.remove_gui_extension_point('plugin_window', self)
        del app.interface.instances['plugins']

    def on_configure_plugin_button_clicked(self, widget):
        selection = self.installed_plugins_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            plugin = model.get_value(iter_, Column.PLUGIN)

            if isinstance(plugin.config_dialog, GajimPluginConfigDialog):
                plugin.config_dialog.run(self.window)
            else:
                plugin.config_dialog(self.window)

        else:
            # No plugin selected. this should never be reached. As configure
            # plugin button should only be clickable when plugin is selected.
            # XXX: maybe throw exception here?
            pass

    def on_uninstall_plugin_button_clicked(self, widget):
        selection = self.installed_plugins_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            plugin = model.get_value(iter_, Column.PLUGIN)
            try:
                app.plugin_manager.uninstall_plugin(plugin)
            except PluginsystemError as e:
                WarningDialog(_('Unable to properly remove the plugin'),
                    str(e), self.window)
                return

    def _on_plugin_removed(self, event):
        for row in self.installed_plugins_model:
            if row[Column.PLUGIN] == event.plugin:
                self.installed_plugins_model.remove(row.iter)
                break

    def _on_plugin_added(self, event):
        icon = self.get_plugin_icon(event.plugin)
        self.installed_plugins_model.append([event.plugin,
                                             event.plugin.name,
                                             False,
                                             event.plugin.activatable,
                                             icon])

    def on_install_plugin_button_clicked(self, widget):
        if app.is_flatpak():
            open_uri('https://dev.gajim.org/gajim/gajim/wikis/help/flathub')
            return

        def show_warn_dialog():
            text = _('Archive is malformed')
            dialog = WarningDialog(text, '', transient_for=self.window)
            dialog.set_modal(False)
            dialog.popup()

        def _on_plugin_exists(zip_filename):
            def _on_yes():
                plugin = app.plugin_manager.install_from_zip(zip_filename,
                                                             True)
                if not plugin:
                    show_warn_dialog()
                    return

            NewConfirmationDialog(
                _('Overwrite Plugin?'),
                _('Plugin already exists'),
                _('Do you want to overwrite the currently installed version?'),
                [DialogButton.make('Cancel'),
                 DialogButton.make('Remove',
                                   text=_('_Overwrite'),
                                   callback=_on_yes)],
                transient_for=self.window).show()

        def _try_install(zip_filename):
            try:
                plugin = app.plugin_manager.install_from_zip(zip_filename)
            except PluginsystemError as er_type:
                error_text = str(er_type)
                if error_text == _('Plugin already exists'):
                    _on_plugin_exists(zip_filename)
                    return

                WarningDialog(error_text, '"%s"' % zip_filename, self.window)
                return
            if not plugin:
                show_warn_dialog()
                return

        ArchiveChooserDialog(_try_install, transient_for=self.window)


class GajimPluginConfigDialog(Gtk.Dialog):
    def __init__(self, plugin, **kwargs):
        Gtk.Dialog.__init__(self, title='%s %s'%(plugin.name,
            _('Configuration')), **kwargs)
        self.plugin = plugin
        button = self.add_button('gtk-close', Gtk.ResponseType.CLOSE)
        button.connect('clicked', self.on_close_button_clicked)

        self.get_child().set_spacing(3)

        self.init()

    def on_close_dialog(self, widget, data):
        self.hide()
        return True

    def on_close_button_clicked(self, widget):
        self.hide()

    def run(self, parent=None):
        self.set_transient_for(parent)
        self.on_run()
        self.show_all()
        self.connect('delete-event', self.on_close_dialog)
        result = super(GajimPluginConfigDialog, self)
        return result

    def init(self):
        pass

    def on_run(self):
        pass
