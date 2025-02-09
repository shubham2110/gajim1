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

import sys
import locale
import logging
from collections import defaultdict

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Pango
from gi.repository import GObject

from gajim.common import app
from gajim.common import passwords
from gajim.common.i18n import _

from gajim.gtk.dialogs import DialogButton
from gajim.gtk.dialogs import NewConfirmationDialog
from gajim.gtk.const import Setting
from gajim.gtk.const import SettingKind
from gajim.gtk.const import SettingType
from gajim.gtk.settings import SettingsDialog
from gajim.gtk.settings import SettingsBox
from gajim.gtk.util import open_window


log = logging.getLogger('gajim.gtk.accounts')


class AccountsWindow(Gtk.ApplicationWindow):
    def __init__(self):
        Gtk.ApplicationWindow.__init__(self)
        self.set_application(app.app)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_show_menubar(False)
        self.set_name('AccountsWindow')
        self.set_default_size(700, 550)
        self.set_resizable(True)
        self.set_title(_('Accounts'))
        self._need_relogin = {}
        self._accounts = {}

        self._menu = AccountMenu()
        self._settings = Settings()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.add(self._menu)
        box.add(self._settings)
        self.add(box)

        for account in app.get_accounts_sorted():
            self.add_account(account, inital=True)

        self._menu.connect('menu-activated', self._on_menu_activated)
        self.connect('destroy', self._on_destroy)
        self.connect('key-press-event', self._on_key_press)

        self.show_all()

    def _on_menu_activated(self, _listbox, account, name):
        if name == 'back':
            self._settings.set_page('add-account')
            self._check_relogin()
        elif name == 'remove':
            self.on_remove_account(account)
        else:
            self._settings.set_page(name)

    def _on_key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def _on_destroy(self, *args):
        self._check_relogin()

    def update_account_label(self, account):
        self._accounts[account].update_account_label()

    def update_proxy_list(self):
        for account in self._accounts:
            self._settings.update_proxy_list(account)

    def _check_relogin(self):
        for account in self._need_relogin:
            settings = self._get_relogin_settings(account)
            active = app.config.get_per('accounts', account, 'active')
            if settings != self._need_relogin[account]:
                self._need_relogin[account] = settings
                if active:
                    self._relog(account)
                break

    def _relog(self, account):
        if app.connections[account].connected == 0:
            return

        if account == app.ZEROCONF_ACC_NAME:
            app.connections[app.ZEROCONF_ACC_NAME].update_details()
            return

        def login(account, show_before, status_before):
            """
            Login with previous status
            """
            # first make sure connection is really closed,
            # 0.5 may not be enough
            app.connections[account].disconnect(True)
            app.interface.roster.send_status(
                account, show_before, status_before)

        def relog(account):
            show_before = app.SHOW_LIST[app.connections[account].connected]
            status_before = app.connections[account].status
            app.interface.roster.send_status(
                account, 'offline', _('Be right back.'))
            GLib.timeout_add(500, login, account, show_before, status_before)

        NewConfirmationDialog(
            _('Re-Login'),
            _('Re-Login now?'),
            _('To apply all changes instantly, you have to re-login.'),
            [DialogButton.make('Cancel',
                               text=_('_Later')),
             DialogButton.make('Accept',
                               text=_('_Re-Login'),
                               callback=lambda *args: relog(account))],
            transient_for=self).show()

    @staticmethod
    def _get_relogin_settings(account):
        if account == app.ZEROCONF_ACC_NAME:
            settings = ['zeroconf_first_name', 'zeroconf_last_name',
                        'zeroconf_jabber_id', 'zeroconf_email']
        else:
            settings = ['client_cert', 'proxy', 'resource',
                        'use_custom_host', 'custom_host', 'custom_port']

        values = []
        for setting in settings:
            values.append(app.config.get_per('accounts', account, setting))
        return values

    @staticmethod
    def on_remove_account(account):
        if app.events.get_events(account):
            app.interface.raise_dialog('unread-events-on-remove-account')
            return

        if app.config.get_per('accounts', account, 'is_zeroconf'):
            # Should never happen as button is insensitive
            return

        open_window('RemoveAccount', account=account)

    def remove_account(self, account):
        del self._need_relogin[account]
        self._accounts[account].remove()

    def add_account(self, account, inital=False):
        self._need_relogin[account] = self._get_relogin_settings(account)
        self._accounts[account] = Account(account, self._menu, self._settings)
        if not inital:
            self._accounts[account].show()

    def select_account(self, account):
        try:
            self._accounts[account].select()
        except KeyError:
            log.warning('select_account() failed, account %s not found',
                        account)


class Settings(Gtk.ScrolledWindow):
    def __init__(self):
        Gtk.ScrolledWindow.__init__(self)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.add_named(AddNewAccountPage(), 'add-account')
        self.get_style_context().add_class('accounts-settings')

        self.add(self._stack)
        self._page_signal_ids = {}
        self._pages = defaultdict(list)

    def add_page(self, page):
        self._pages[page.account].append(page)
        self._stack.add_named(page, '%s-%s' % (page.account, page.name))
        self._page_signal_ids[page] = page.connect_signal(self._stack)

    def set_page(self, name):
        self._stack.set_visible_child_name(name)

    def remove_account(self, account):
        for page in self._pages[account]:
            signal_id = self._page_signal_ids[page]
            del self._page_signal_ids[page]
            self._stack.disconnect(signal_id)
            self._stack.remove(page)
            page.destroy()
        del self._pages[account]

    def update_proxy_list(self, account):
        for page in self._pages[account]:
            if page.name != 'connection':
                continue
            page.listbox.get_setting('proxy').update_values()


class AccountMenu(Gtk.Box):

    __gsignals__ = {
        'menu-activated': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    def __init__(self):
        Gtk.Box.__init__(self)
        self.set_hexpand(False)
        self.set_size_request(160, -1)

        self.get_style_context().add_class('accounts-menu')

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)

        self._accounts_listbox = Gtk.ListBox()
        self._accounts_listbox.set_sort_func(self._sort_func)
        self._accounts_listbox.get_style_context().add_class('settings-box')
        self._accounts_listbox.connect('row-activated',
                                       self._on_account_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self._accounts_listbox)
        self._stack.add_named(scrolled, 'accounts')
        self.add(self._stack)

    @staticmethod
    def _sort_func(row1, row2):
        if row1.label == 'Local':
            return -1
        return locale.strcoll(row1.label.lower(), row2.label.lower())

    def add_account(self, row):
        self._accounts_listbox.add(row)
        sub_menu = AccountSubMenu(row.account)
        self._stack.add_named(sub_menu, '%s-menu' % row.account)

        sub_menu.connect('row-activated', self._on_sub_menu_row_activated)

    def remove_account(self, row):
        if self._stack.get_visible_child_name() != 'accounts':
            # activate 'back' button
            self._stack.get_visible_child().get_row_at_index(1).emit('activate')
        self._accounts_listbox.remove(row)
        sub_menu = self._stack.get_child_by_name('%s-menu' % row.account)
        self._stack.remove(sub_menu)
        row.destroy()
        sub_menu.destroy()

    def _on_account_row_activated(self, _listbox, row):
        self._stack.set_visible_child_name('%s-menu' % row.account)
        self._stack.get_visible_child().get_row_at_index(2).emit('activate')

    def _on_sub_menu_row_activated(self, listbox, row):
        if row.name == 'back':
            self._stack.set_visible_child_full(
                'accounts', Gtk.StackTransitionType.OVER_RIGHT)

        if row.name in ('back', 'remove'):
            self.emit('menu-activated', listbox.account, row.name)

        else:
            self.emit('menu-activated',
                      listbox.account,
                      '%s-%s' % (listbox.account, row.name))

    def update_account_label(self, account):
        self._accounts_listbox.invalidate_sort()
        sub_menu = self._stack.get_child_by_name('%s-menu' % account)
        sub_menu.update()


class AccountSubMenu(Gtk.ListBox):

    __gsignals__ = {
        'update': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, account):
        Gtk.ListBox.__init__(self)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.get_style_context().add_class('settings-box')

        self._account = account

        self.add(AccountLabelMenuItem(self, self._account))
        self.add(BackMenuItem())
        self.add(PageMenuItem('general', _('General')))
        if account != 'Local':
            self.add(PageMenuItem('privacy', _('Privacy')))
            self.add(PageMenuItem('connection', _('Connection')))
            self.add(RemoveMenuItem())

    @property
    def account(self):
        return self._account

    def update(self):
        self.emit('update', self._account)


class MenuItem(Gtk.ListBoxRow):
    def __init__(self, name):
        Gtk.ListBoxRow.__init__(self)
        self._name = name
        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                            spacing=12)
        self._label = Gtk.Label()

        self.add(self._box)

    @property
    def name(self):
        return self._name


class RemoveMenuItem(MenuItem):
    def __init__(self):
        super().__init__('remove')
        self._label.set_text(_('Remove'))
        image = Gtk.Image.new_from_icon_name('user-trash-symbolic',
                                             Gtk.IconSize.MENU)

        self.set_selectable(False)
        image.get_style_context().add_class('error-color')

        self._box.add(image)
        self._box.add(self._label)


class AccountLabelMenuItem(MenuItem):
    def __init__(self, parent, account):
        super().__init__('account-label')
        self._update_account_label(parent, account)

        self.set_selectable(False)
        self.set_sensitive(False)
        self.set_activatable(False)

        image = Gtk.Image.new_from_icon_name('avatar-default-symbolic',
                                             Gtk.IconSize.MENU)
        image.get_style_context().add_class('insensitive-fg-color')

        self._label.get_style_context().add_class('accounts-label-row')
        self._label.set_ellipsize(Pango.EllipsizeMode.END)
        self._label.set_xalign(0)

        self._box.add(image)
        self._box.add(self._label)

        parent.connect('update', self._update_account_label)

    def _update_account_label(self, _listbox, account):
        account_label = app.get_account_label(account)
        self._label.set_text(account_label)


class BackMenuItem(MenuItem):
    def __init__(self):
        super().__init__('back')
        self.set_selectable(False)

        self._label.set_text(_('Back'))

        image = Gtk.Image.new_from_icon_name('go-previous-symbolic',
                                             Gtk.IconSize.MENU)
        image.get_style_context().add_class('insensitive-fg-color')

        self._box.add(image)
        self._box.add(self._label)


class PageMenuItem(MenuItem):
    def __init__(self, name, label):
        super().__init__(name)

        if name == 'general':
            icon = 'preferences-system-symbolic'
        elif name == 'privacy':
            icon = 'preferences-system-privacy-symbolic'
        elif name == 'connection':
            icon = 'preferences-system-network-symbolic'
        else:
            icon = 'dialog-error-symbolic'

        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
        self._label.set_text(label)

        self._box.add(image)
        self._box.add(self._label)


class Account:
    def __init__(self, account, menu, settings):
        self._account = account
        self._menu = menu
        self._settings = settings

        if account == app.ZEROCONF_ACC_NAME:
            self._settings.add_page(ZeroConfPage(account))
        else:
            self._settings.add_page(GeneralPage(account))
            self._settings.add_page(ConnectionPage(account))
            self._settings.add_page(PrivacyPage(account))

        self._account_row = AccountRow(account)
        self._menu.add_account(self._account_row)

    def select(self):
        self._account_row.emit('activate')

    def show(self):
        self._menu.show_all()
        self._settings.show_all()
        self.select()

    def remove(self):
        self._menu.remove_account(self._account_row)
        self._settings.remove_account(self._account)

    def update_account_label(self):
        self._account_row.update_account_label()
        self._menu.update_account_label(self._account)

    @property
    def menu(self):
        return self._menu

    @property
    def account(self):
        return self._account

    @property
    def settings(self):
        return self._account


class AccountRow(Gtk.ListBoxRow):
    def __init__(self, account):
        Gtk.ListBoxRow.__init__(self)
        self.set_selectable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self._account = account

        self._label = Gtk.Label(label=app.get_account_label(account))
        self._label.set_halign(Gtk.Align.START)
        self._label.set_hexpand(True)
        self._label.set_ellipsize(Pango.EllipsizeMode.END)
        self._label.set_xalign(0)
        self._label.set_width_chars(18)

        next_icon = Gtk.Image.new_from_icon_name('go-next-symbolic',
                                                 Gtk.IconSize.MENU)
        next_icon.get_style_context().add_class('insensitive-fg-color')

        switch = Gtk.Switch()
        switch.set_active(
            app.config.get_per('accounts', self._account, 'active'))
        switch.set_vexpand(False)

        if (self._account == app.ZEROCONF_ACC_NAME and
                not app.is_installed('ZEROCONF')):
            switch.set_active(False)
            self.set_activatable(False)
            self.set_sensitive(False)
            if sys.platform in ('win32', 'darwin'):
                tooltip = _('Please check if Bonjour is installed.')
            else:
                tooltip = _('Please check if Avahi is installed.')
            self.set_tooltip_text(tooltip)

        switch.connect('state-set', self._on_enable_switch, self._account)

        box.add(switch)
        box.add(self._label)
        box.add(next_icon)
        self.add(box)

    @property
    def account(self):
        return self._account

    @property
    def label(self):
        return self._label.get_text()

    def update_account_label(self):
        self._label.set_text(app.get_account_label(self._account))

    def _on_enable_switch(self, switch, state, account):
        def _disable():
            app.connections[account].change_status('offline', 'offline')
            app.connections[account].disconnect(reconnect=False)
            app.interface.disable_account(account)
            switch.set_state(state)

        old_state = app.config.get_per('accounts', account, 'active')
        if old_state == state:
            return Gdk.EVENT_PROPAGATE

        if (account in app.connections and
                app.connections[account].connected > 0):
            # Connecting or connected
            NewConfirmationDialog(
                _('Disable Account'),
                _('Account %s is still connected') % account,
                _('All chat and group chat windows will be closed.'),
                [DialogButton.make('Cancel',
                                   callback=lambda: switch.set_active(True)),
                 DialogButton.make('Remove',
                                   text=_('_Disable Account'),
                                   callback=_disable)],
                transient_for=self.get_toplevel()).show()
            return Gdk.EVENT_STOP

        if state:
            app.interface.enable_account(account)
        else:
            app.interface.disable_account(account)

        return Gdk.EVENT_PROPAGATE


class AddNewAccountPage(Gtk.Box):
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_vexpand(True)
        self.set_hexpand(True)
        button = Gtk.Button(label=_('Add Account'))
        button.get_style_context().add_class('suggested-action')
        button.set_action_name('app.add-account')
        button.set_halign(Gtk.Align.CENTER)
        button.set_valign(Gtk.Align.CENTER)
        self.add(button)


class GenericSettingPage(Gtk.Box):
    def __init__(self, account, settings):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_valign(Gtk.Align.START)
        self.set_vexpand(True)
        self.account = account

        self.listbox = SettingsBox(account)
        self.listbox.get_style_context().add_class('accounts-settings-border')
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.set_vexpand(False)
        self.listbox.set_valign(Gtk.Align.END)

        for setting in settings:
            self.listbox.add_setting(setting)
        self.listbox.update_states()

        self.pack_end(self.listbox, True, True, 0)

        self.listbox.connect('row-activated', self.on_row_activated)

    def connect_signal(self, stack):
        return stack.connect('notify::visible-child',
                             self._on_visible_child_changed)

    def _on_visible_child_changed(self, stack, _param):
        if self == stack.get_visible_child():
            self.listbox.update_states()

    @staticmethod
    def on_row_activated(_listbox, row):
        row.on_row_activated()


class GeneralPage(GenericSettingPage):

    name = 'general'

    def __init__(self, account):

        settings = [
            Setting(SettingKind.ENTRY, _('Label'),
                    SettingType.ACCOUNT_CONFIG, 'account_label',
                    callback=self._on_account_name_change),

            Setting(SettingKind.LOGIN, _('Login'), SettingType.DIALOG,
                    props={'dialog': LoginDialog}),

            Setting(SettingKind.ACTION, _('Import Contacts'),
                    SettingType.ACTION, '-import-contacts',
                    props={'account': account}),

            Setting(SettingKind.DIALOG, _('Client Certificate'),
                    SettingType.DIALOG, props={'dialog': CertificateDialog}),

            Setting(SettingKind.SWITCH, _('Connect on startup'),
                    SettingType.ACCOUNT_CONFIG, 'autoconnect'),

            Setting(SettingKind.SWITCH,
                    _('Save conversations for all contacts'),
                    SettingType.ACCOUNT_CONFIG, 'no_log_for',
                    desc=_('Store conversations on the harddrive')),

            Setting(SettingKind.SWITCH, _('Global Status'),
                    SettingType.ACCOUNT_CONFIG, 'sync_with_global_status',
                    desc=_('Synchronise the status of all accounts')),

            Setting(SettingKind.SWITCH, _('Use file transfer proxies'),
                    SettingType.ACCOUNT_CONFIG, 'use_ft_proxies'),
        ]
        GenericSettingPage.__init__(self, account, settings)

    def _on_account_name_change(self, *args):
        self.get_toplevel().update_account_label(self.account)


class PrivacyPage(GenericSettingPage):

    name = 'privacy'

    def __init__(self, account):

        settings = [
            Setting(SettingKind.SWITCH, _('Idle Time'),
                    SettingType.ACCOUNT_CONFIG, 'send_idle_time',
                    desc=_('Disclose the time of your last activity')),

            Setting(SettingKind.SWITCH, _('Local System Time'),
                    SettingType.ACCOUNT_CONFIG, 'send_time_info',
                    desc=_('Disclose the local system time of the '
                           'device Gajim runs on')),

            Setting(SettingKind.SWITCH, _('Client / Operating System'),
                    SettingType.ACCOUNT_CONFIG, 'send_os_info',
                    desc=_('Disclose informations about the client '
                           'and operating system you currently use')),

            Setting(SettingKind.SWITCH, _('Ignore Unknown Contacts'),
                    SettingType.ACCOUNT_CONFIG, 'ignore_unknown_contacts',
                    desc=_('Ignore everything from contacts not in your '
                           'Roster')),

            ]
        GenericSettingPage.__init__(self, account, settings)


class ConnectionPage(GenericSettingPage):

    name = 'connection'

    def __init__(self, account):

        settings = [
            Setting(SettingKind.SWITCH, 'HTTP_PROXY',
                    SettingType.ACCOUNT_CONFIG, 'use_env_http_proxy',
                    desc=_('Use environment variable')),

            Setting(SettingKind.PROXY, _('Proxy'),
                    SettingType.ACCOUNT_CONFIG, 'proxy', name='proxy'),

            Setting(SettingKind.SWITCH, _('Warn on insecure connection'),
                    SettingType.ACCOUNT_CONFIG,
                    'warn_when_insecure_ssl_connection'),

            Setting(SettingKind.SWITCH, _('Send keep-alive packets'),
                    SettingType.ACCOUNT_CONFIG, 'keep_alives_enabled'),

            Setting(SettingKind.HOSTNAME, _('Hostname'), SettingType.DIALOG,
                    desc=_('Manually set the hostname for the server'),
                    props={'dialog': CutstomHostnameDialog}),

            Setting(SettingKind.ENTRY, _('Resource'),
                    SettingType.ACCOUNT_CONFIG, 'resource'),

            Setting(SettingKind.PRIORITY, _('Priority'),
                    SettingType.DIALOG, props={'dialog': PriorityDialog}),
            ]

        GenericSettingPage.__init__(self, account, settings)


class ZeroConfPage(GenericSettingPage):

    name = 'general'

    def __init__(self, account):

        settings = [
            Setting(SettingKind.DIALOG, _('Profile'),
                    SettingType.DIALOG,
                    props={'dialog': ZeroconfProfileDialog}),

            Setting(SettingKind.SWITCH, _('Connect on startup'),
                    SettingType.ACCOUNT_CONFIG, 'autoconnect',
                    desc=_('Use environment variable')),

            Setting(SettingKind.SWITCH,
                    _('Save conversations for all contacts'),
                    SettingType.ACCOUNT_CONFIG, 'no_log_for',
                    desc=_('Store conversations on the harddrive')),

            Setting(SettingKind.SWITCH, _('Global Status'),
                    SettingType.ACCOUNT_CONFIG, 'sync_with_global_status',
                    desc=_('Synchronize the status of all accounts')),
            ]

        GenericSettingPage.__init__(self, account, settings)


class ZeroconfProfileDialog(SettingsDialog):
    def __init__(self, account, parent):

        settings = [
            Setting(SettingKind.ENTRY, _('First Name'),
                    SettingType.ACCOUNT_CONFIG, 'zeroconf_first_name'),

            Setting(SettingKind.ENTRY, _('Last Name'),
                    SettingType.ACCOUNT_CONFIG, 'zeroconf_last_name'),

            Setting(SettingKind.ENTRY, _('XMPP Address'),
                    SettingType.ACCOUNT_CONFIG, 'zeroconf_jabber_id'),

            Setting(SettingKind.ENTRY, _('Email'),
                    SettingType.ACCOUNT_CONFIG, 'zeroconf_email'),
            ]

        SettingsDialog.__init__(self, parent, _('Profile'),
                                Gtk.DialogFlags.MODAL, settings, account)


class PriorityDialog(SettingsDialog):
    def __init__(self, account, parent):

        neg_priority = app.config.get('enable_negative_priority')
        if neg_priority:
            range_ = (-128, 127)
        else:
            range_ = (0, 127)

        settings = [
            Setting(SettingKind.SWITCH, _('Adjust to status'),
                    SettingType.ACCOUNT_CONFIG, 'adjust_priority_with_status',
                    'adjust'),

            Setting(SettingKind.SPIN, _('Priority'),
                    SettingType.ACCOUNT_CONFIG, 'priority',
                    enabledif=('adjust', False), props={'range_': range_}),
            ]

        SettingsDialog.__init__(self, parent, _('Priority'),
                                Gtk.DialogFlags.MODAL, settings, account)

        self.connect('destroy', self.on_destroy)

    def on_destroy(self, *args):
        # Update priority
        if self.account not in app.connections:
            return
        show = app.SHOW_LIST[app.connections[self.account].connected]
        status = app.connections[self.account].status
        app.connections[self.account].change_status(show, status)


class CutstomHostnameDialog(SettingsDialog):
    def __init__(self, account, parent):

        settings = [
            Setting(SettingKind.SWITCH, _('Enable'),
                    SettingType.ACCOUNT_CONFIG,
                    'use_custom_host', name='custom'),

            Setting(SettingKind.ENTRY, _('Hostname'),
                    SettingType.ACCOUNT_CONFIG, 'custom_host',
                    enabledif=('custom', True)),

            Setting(SettingKind.ENTRY, _('Port'),
                    SettingType.ACCOUNT_CONFIG, 'custom_port',
                    enabledif=('custom', True)),
            ]

        SettingsDialog.__init__(self, parent, _('Connection Settings'),
                                Gtk.DialogFlags.MODAL, settings, account)


class CertificateDialog(SettingsDialog):
    def __init__(self, account, parent):

        settings = [
            Setting(SettingKind.FILECHOOSER, _('Client Certificate'),
                    SettingType.ACCOUNT_CONFIG, 'client_cert',
                    props={'filefilter': (_('PKCS12 Files'), '*.p12')}),

            Setting(SettingKind.SWITCH, _('Encrypted Certificate'),
                    SettingType.ACCOUNT_CONFIG, 'client_cert_encrypted'),
            ]

        SettingsDialog.__init__(self, parent, _('Certificate Settings'),
                                Gtk.DialogFlags.MODAL, settings, account)


class LoginDialog(SettingsDialog):
    def __init__(self, account, parent):

        settings = [
            Setting(SettingKind.ENTRY, _('Password'),
                    SettingType.ACCOUNT_CONFIG, 'password', name='password',
                    enabledif=('savepass', True)),

            Setting(SettingKind.SWITCH, _('Save Password'),
                    SettingType.ACCOUNT_CONFIG, 'savepass', name='savepass'),

            Setting(SettingKind.CHANGEPASSWORD, _('Change Password'),
                    SettingType.DIALOG, callback=self.on_password_change,
                    props={'dialog': None}),
            ]

        SettingsDialog.__init__(self, parent, _('Login Settings'),
                                Gtk.DialogFlags.MODAL, settings, account)

        self.connect('destroy', self.on_destroy)

    def on_password_change(self, new_password, _data):
        passwords.save_password(self.account, new_password)

    def on_destroy(self, *args):
        savepass = app.config.get_per('accounts', self.account, 'savepass')
        if not savepass:
            passwords.delete_password(self.account)
