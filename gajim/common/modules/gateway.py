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

# XEP-0100: Gateway Interaction

import nbxmpp

from gajim.common import app
from gajim.common.nec import NetworkEvent
from gajim.common.modules.base import BaseModule


class Gateway(BaseModule):
    def __init__(self, con):
        BaseModule.__init__(self, con)

    def unsubscribe(self, agent):
        if not app.account_is_connected(self._account):
            return
        iq = nbxmpp.Iq('set', nbxmpp.NS_REGISTER, to=agent)
        iq.setQuery().setTag('remove')

        self._con.connection.SendAndCallForResponse(
            iq, self._on_unsubscribe_result)
        self._con.get_module('Roster').del_item(agent)

    def _on_unsubscribe_result(self, stanza):
        if not nbxmpp.isResultNode(stanza):
            self._log.info('Error: %s', stanza.getError())
            return

        agent = stanza.getFrom().getBare()
        jid_list = []
        for jid in app.contacts.get_jid_list(self._account):
            if jid.endswith('@' + agent):
                jid_list.append(jid)
                self._log.info('Removing contact %s due to'
                               ' unregistered transport %s', jid, agent)
                self._con.get_module('Presence').unsubscribe(jid)
                # Transport contacts can't have 2 resources
                if jid in app.to_be_removed[self._account]:
                    # This way we'll really remove it
                    app.to_be_removed[self._account].remove(jid)

        app.nec.push_incoming_event(
            NetworkEvent('agent-removed',
                         conn=self._con,
                         agent=agent,
                         jid_list=jid_list))

    def request_gateway_prompt(self, jid, prompt=None):
        typ_ = 'get'
        if prompt:
            typ_ = 'set'
        iq = nbxmpp.Iq(typ=typ_, to=jid)
        query = iq.addChild(name='query', namespace=nbxmpp.NS_GATEWAY)
        if prompt:
            query.setTagData('prompt', prompt)
        self._con.connection.SendAndCallForResponse(iq, self._on_prompt_result)

    def _on_prompt_result(self, stanza):
        jid = str(stanza.getFrom())
        fjid = stanza.getFrom().getBare()
        resource = stanza.getFrom().getResource()

        query = stanza.getTag('query')
        if query is not None:
            desc = query.getTagData('desc')
            prompt = query.getTagData('prompt')
            prompt_jid = query.getTagData('jid')
        else:
            desc = None
            prompt = None
            prompt_jid = None

        app.nec.push_incoming_event(
            NetworkEvent('gateway-prompt-received',
                         conn=self._con,
                         fjid=fjid,
                         jid=jid,
                         resource=resource,
                         desc=desc,
                         prompt=prompt,
                         prompt_jid=prompt_jid,
                         stanza=stanza))


def get_instance(*args, **kwargs):
    return Gateway(*args, **kwargs), 'Gateway'
