# Copyright (C) 2007 Jean-Marie Traissard <jim AT lapin.org>
#                    Julien Pivotto <roidelapluie AT gmail.com>
#                    Stefan Bethge <stefan AT lanpartei.de>
#                    Stephan Erb <steve-e AT h3c.de>
# Copyright (C) 2007-2014 Yann Leboulanger <asterix AT lagaule.org>
# Copyright (C) 2008 Jonathan Schleifer <js-gajim AT webkeks.org>
#
# This file is part of Gajim.
#
# Gajim is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation; version 3 only.
#
# Gajim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gajim. If not, see <http://www.gnu.org/licenses/>.

import os
from collections import namedtuple

import gi
from gi.repository import Gtk

from gajim.common import app
from gajim.common.i18n import _


class FeaturesDialog(Gtk.Dialog):
    def __init__(self):
        super().__init__(title=_('Features'),
                         transient_for=None,
                         destroy_with_parent=True)

        self.set_transient_for(app.interface.roster.window)
        self.set_resizable(False)

        grid = Gtk.Grid()
        grid.set_name('FeaturesInfoGrid')
        grid.set_row_spacing(10)
        grid.set_hexpand(True)

        self.feature_listbox = Gtk.ListBox()
        self.feature_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.feature_listbox.set_header_func(self.header_func, _('Features'))

        grid.attach(self.feature_listbox, 0, 0, 1, 1)

        box = self.get_content_area()
        box.pack_start(grid, True, True, 0)
        box.set_property('margin', 12)
        box.set_spacing(18)

        self.connect('response', self.on_response)

        for feature in self.get_features():
            self.add_feature(feature)

        self.show_all()

    @staticmethod
    def header_func(row, before, user_data):
        if before:
            row.set_header(None)
        else:
            label = Gtk.Label(label=user_data)
            label.set_halign(Gtk.Align.START)
            row.set_header(label)

    def on_response(self, _dialog, response):
        if response == Gtk.ResponseType.OK:
            self.destroy()

    def add_feature(self, feature):
        item = FeatureItem(feature)
        self.feature_listbox.add(item)
        item.get_parent().set_tooltip_text(item.tooltip)

    def get_features(self):
        Feature = namedtuple('Feature',
                             ['name', 'available', 'tooltip',
                              'dependency_u', 'dependency_w', 'enabled'])

        spell_check_enabled = app.config.get('use_speller')

        auto_status = [app.config.get('autoaway'), app.config.get('autoxa')]
        auto_status_enabled = bool(any(auto_status))

        return [
            Feature(_('Audio / Video'),
                    app.is_installed('FARSTREAM'),
                    _('Enables Gajim to provide Audio and Video chats'),
                    _('Requires: gir1.2-farstream-0.2, gir1.2-gstreamer-1.0, '
                      'gstreamer1.0-libav, gstreamer1.0-plugins-ugly'),
                    _('Feature not available under Windows'),
                    None),
            Feature(_('Automatic Status'),
                    self.idle_available(),
                    _('Enables Gajim to measure your computer\'s idle time in '
                      'order to set your Status automatically'),
                    _('Requires: libxss'),
                    _('No additional requirements'),
                    auto_status_enabled),
            Feature(_('Bonjour / Zeroconf (Serverless Chat)'),
                    app.is_installed('ZEROCONF'),
                    _('Enables Gajim to automatically detected clients in a '
                      'local network for serverless chats'),
                    _('Requires: gir1.2-avahi-0.6'),
                    _('Requires: pybonjour and bonjour SDK running (%(url)s)')
                    % {'url': 'https://developer.apple.com/opensource/)'},
                    None),
            Feature(_('Secure Password Storage'),
                    self.some_keyring_available(),
                    _('Enables Gajim to store Passwords securely instead of '
                      'storing them in plaintext'),
                    _('Requires: libsecret and a provider (such as GNOME '
                      'Keyring and KSecretService)'),
                    _('Windows Credential Vault is used for secure password '
                      'storage'),
                    None),
            Feature(_('Spell Checker'),
                    app.is_installed('GSPELL'),
                    _('Enables Gajim to spell check your messages while '
                      'composing'),
                    _('Requires: Gspell'),
                    _('Requires: Gspell'),
                    spell_check_enabled),
            Feature(_('UPnP-IGD Port Forwarding'),
                    app.is_installed('UPNP'),
                    _('Enables Gajim to request your router to forward ports '
                      'for file transfers'),
                    _('Requires: gir1.2-gupnpigd-1.0'),
                    _('Feature not available under Windows'),
                    None)
        ]

    @staticmethod
    def some_keyring_available():
        if os.name == 'nt':
            return True
        try:
            gi.require_version('Secret', '1')
            from gi.repository import Secret  # pylint: disable=unused-import
        except (ValueError, ImportError):
            return False
        return True

    @staticmethod
    def idle_available():
        from gajim.common import idle
        return idle.Monitor.is_available()


class FeatureItem(Gtk.Grid):
    def __init__(self, feature):
        super().__init__()
        self.set_column_spacing(12)

        self.tooltip = feature.tooltip
        self.feature_dependency_u_text = feature.dependency_u
        self.feature_dependency_w_text = feature.dependency_w

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.feature_label = Gtk.Label(label=feature.name)
        self.feature_label.set_halign(Gtk.Align.START)
        self.box.pack_start(self.feature_label, True, True, 0)

        self.feature_dependency_u = Gtk.Label(label=feature.dependency_u)
        self.feature_dependency_u.get_style_context().add_class('dim-label')
        self.feature_dependency_w = Gtk.Label(label=feature.dependency_w)
        self.feature_dependency_w.get_style_context().add_class('dim-label')

        if not feature.available:
            self.feature_dependency_u.set_halign(Gtk.Align.START)
            self.feature_dependency_u.set_xalign(0.0)
            self.feature_dependency_u.set_yalign(0.0)
            self.feature_dependency_u.set_line_wrap(True)
            self.feature_dependency_u.set_max_width_chars(50)
            self.feature_dependency_u.set_selectable(True)
            self.feature_dependency_w.set_halign(Gtk.Align.START)
            self.feature_dependency_w.set_xalign(0.0)
            self.feature_dependency_w.set_yalign(0.0)
            self.feature_dependency_w.set_line_wrap(True)
            self.feature_dependency_w.set_max_width_chars(50)
            self.feature_dependency_w.set_selectable(True)

            if os.name == 'nt':
                self.box.pack_start(self.feature_dependency_w, True, True, 0)
            else:
                self.box.pack_start(self.feature_dependency_u, True, True, 0)

        self.icon = Gtk.Image()
        self.label_disabled = Gtk.Label(label=_('Disabled in Preferences'))
        self.label_disabled.get_style_context().add_class('dim-label')
        self.set_feature(feature.available, feature.enabled)

        self.add(self.icon)
        self.add(self.box)

    def set_feature(self, available, enabled):
        self.icon.get_style_context().remove_class('error-color')
        self.icon.get_style_context().remove_class('warning-color')
        self.icon.get_style_context().remove_class('success-color')

        if not available:
            self.icon.set_from_icon_name('window-close-symbolic',
                                         Gtk.IconSize.MENU)
            self.icon.get_style_context().add_class('error-color')
        elif enabled is False:
            self.icon.set_from_icon_name('dialog-warning-symbolic',
                                         Gtk.IconSize.MENU)
            self.box.pack_start(self.label_disabled, True, True, 0)
            self.icon.get_style_context().add_class('warning-color')
        else:
            self.icon.set_from_icon_name('emblem-ok-symbolic',
                                         Gtk.IconSize.MENU)
            self.icon.get_style_context().add_class('success-color')
