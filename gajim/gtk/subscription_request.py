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

from gi.repository import Gtk

from gajim import vcard

from gajim.common import app
from gajim.common.i18n import _

from gajim.gtk.add_contact import AddNewContactWindow
from gajim.gtk.util import get_builder


class SubscriptionRequest(Gtk.ApplicationWindow):
    def __init__(self, account, jid, text, user_nick=None):
        Gtk.ApplicationWindow.__init__(self)
        self.set_name('SubscriptionRequest')
        self.set_application(app.app)
        self.set_show_menubar(False)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_title(_('Subscription Request'))

        self._ui = get_builder('subscription_request_window.ui')
        self.add(self._ui.subscription_box)
        self.jid = jid
        self.account = account
        self.user_nick = user_nick
        self._ui.jid_label.set_text(self.jid)
        if len(app.connections) >= 2:
            prompt_text = \
                _('Subscription request for account %(account)s from %(jid)s')\
                % {'account': account, 'jid': self.jid}
        else:
            prompt_text = _('Subscription request from %s') % self.jid

        self._ui.request_label.set_text(prompt_text)
        self._ui.subscription_text.set_text(text)

        self._ui.connect_signals(self)
        self.show_all()

    def _on_authorize_clicked(self, _widget):
        """
        Accept the request
        """
        con = app.connections[self.account]
        con.get_module('Presence').subscribed(self.jid)
        self.destroy()
        contact = app.contacts.get_contact(self.account, self.jid)
        if not contact or _('Not in contact list') in contact.groups:
            AddNewContactWindow(self.account, self.jid, self.user_nick)

    def _on_contact_info_clicked(self, _widget):
        """
        Ask for vCard
        """
        open_windows = app.interface.instances[self.account]['infos']
        if self.jid in open_windows:
            open_windows[self.jid].window.present()
        else:
            contact = app.contacts.create_contact(jid=self.jid,
                                                  account=self.account)
            app.interface.instances[self.account]['infos'][self.jid] = \
                     vcard.VcardWindow(contact, self.account)
            # Remove xmpp page
            app.interface.instances[self.account]['infos'][self.jid].xml.\
                     get_object('information_notebook').remove_page(0)

    def _on_start_chat_clicked(self, _widget):
        """
        Open chat
        """
        app.interface.new_chat_from_jid(self.account, self.jid)

    def _on_deny_clicked(self, _widget):
        """
        Refuse the request
        """
        con = app.connections[self.account]
        con.get_module('Presence').unsubscribed(self.jid)
        contact = app.contacts.get_contact(self.account, self.jid)
        if contact and _('Not in contact list') in contact.get_shown_groups():
            app.interface.roster.remove_contact(self.jid, self.account)
        self.destroy()
