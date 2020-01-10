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
# along with Gajim.  If not, see <http://www.gnu.org/licenses/>.

# XEP-0313: Message Archive Management

import time
from datetime import datetime, timedelta

import nbxmpp
from nbxmpp.structs import StanzaHandler

from gajim.common import app
from gajim.common.nec import NetworkEvent
from gajim.common.nec import NetworkIncomingEvent
from gajim.common.const import ArchiveState
from gajim.common.const import KindConstant
from gajim.common.const import SyncThreshold
from gajim.common.helpers import get_sync_threshold
from gajim.common.helpers import AdditionalDataDict
from gajim.common.modules.misc import parse_oob
from gajim.common.modules.misc import parse_correction
from gajim.common.modules.util import get_eme_message
from gajim.common.modules.base import BaseModule


class MAM(BaseModule):
    def __init__(self, con):
        BaseModule.__init__(self, con)

        self.handlers = [
            StanzaHandler(name='message',
                          callback=self._set_message_archive_info,
                          priority=41),
            StanzaHandler(name='message',
                          callback=self._mam_message_received,
                          priority=51),
        ]

        self.available = False
        self.archiving_namespace = None
        self._mam_query_ids = {}

        # Holds archive jids where catch up was successful
        self._catch_up_finished = []

    def pass_disco(self, info):
        if nbxmpp.NS_MAM_2 in info.features:
            self.archiving_namespace = nbxmpp.NS_MAM_2
        elif nbxmpp.NS_MAM_1 in info.features:
            self.archiving_namespace = nbxmpp.NS_MAM_1
        else:
            return

        self.available = True
        self._log.info('Discovered MAM %s: %s',
                       self.archiving_namespace, info.jid)

        app.nec.push_incoming_event(
            NetworkEvent('feature-discovered',
                         account=self._account,
                         feature=self.archiving_namespace))

    def reset_state(self):
        self._mam_query_ids.clear()
        self._catch_up_finished.clear()

    def is_catch_up_finished(self, jid):
        return jid in self._catch_up_finished

    def _from_valid_archive(self, _stanza, properties):
        if properties.type.is_groupchat:
            expected_archive = properties.jid
        else:
            expected_archive = self._con.get_own_jid()

        return properties.mam.archive.bareMatch(expected_archive)

    def _get_unique_id(self, properties):
        if properties.type.is_groupchat:
            return properties.mam.id, None

        if properties.is_self_message:
            return None, properties.id

        if properties.is_muc_pm:
            return properties.mam.id, properties.id

        if self._con.get_own_jid().bareMatch(properties.from_):
            # message we sent
            return properties.mam.id, properties.id

        # A message we received
        return properties.mam.id, None

    def _set_message_archive_info(self, _con, _stanza, properties):
        if (properties.is_mam_message or
                properties.is_pubsub or
                properties.is_muc_subject):
            return

        if properties.type.is_groupchat:
            archive_jid = properties.jid.getBare()
            disco_info = app.logger.get_last_disco_info(archive_jid)
            if disco_info is None:
                # This is the case on MUC creation
                # After MUC configuration we receive a configuration change
                # message before we had the chance to disco the new MUC
                return
            namespace = disco_info.mam_namespace
            timestamp = properties.timestamp
            if namespace is None:
                # MUC History
                app.logger.set_archive_infos(
                    archive_jid,
                    last_muc_timestamp=timestamp)
                return

        else:
            archive_jid = self._con.get_own_jid().getBare()
            namespace = self.archiving_namespace
            timestamp = None

        if properties.stanza_id is None or namespace != nbxmpp.NS_MAM_2:
            return

        if not archive_jid == properties.stanza_id.by:
            return

        if not self.is_catch_up_finished(archive_jid):
            return

        app.logger.set_archive_infos(archive_jid,
                                     last_mam_id=properties.stanza_id.id,
                                     last_muc_timestamp=timestamp)

    def _mam_message_received(self, _con, stanza, properties):
        if not properties.is_mam_message:
            return

        app.nec.push_incoming_event(
            NetworkIncomingEvent('mam-message-received',
                                 account=self._account,
                                 stanza=stanza,
                                 properties=properties))

        if not self._from_valid_archive(stanza, properties):
            self._log.warning('Message from invalid archive %s',
                              properties.mam.archive)
            raise nbxmpp.NodeProcessed

        self._log.info('Received message from archive: %s',
                       properties.mam.archive)
        if not self._is_valid_request(properties):
            self._log.warning('Invalid MAM Message: unknown query id %s',
                              properties.mam.query_id)
            self._log.debug(stanza)
            raise nbxmpp.NodeProcessed

        is_groupchat = properties.type.is_groupchat
        if is_groupchat:
            kind = KindConstant.GC_MSG
        else:
            if properties.from_.bareMatch(self._con.get_own_jid()):
                kind = KindConstant.CHAT_MSG_SENT
            else:
                kind = KindConstant.CHAT_MSG_RECV

        stanza_id, message_id = self._get_unique_id(properties)

        if properties.mam.is_ver_2:
            # Search only with stanza-id for duplicates on mam:2
            if app.logger.find_stanza_id(self._account,
                                         str(properties.mam.archive),
                                         stanza_id,
                                         message_id,
                                         groupchat=is_groupchat):
                self._log.info('Found duplicate with stanza-id: %s, '
                               'message-id: %s', stanza_id, message_id)
                raise nbxmpp.NodeProcessed

        additional_data = AdditionalDataDict()
        if properties.has_user_delay:
            # Record it as a user timestamp
            additional_data.set_value(
                'gajim', 'user_timestamp', properties.user_timestamp)

        parse_oob(properties, additional_data)

        msgtxt = properties.body

        if properties.is_encrypted:
            additional_data['encrypted'] = properties.encrypted.additional_data
        else:
            if properties.eme is not None:
                msgtxt = get_eme_message(properties.eme)

        if not msgtxt:
            # For example Chatstates, Receipts, Chatmarkers
            self._log.debug(stanza.getProperties())
            return

        with_ = properties.jid.getStripped()
        if properties.is_muc_pm:
            # we store the message with the full JID
            with_ = str(with_)

        if properties.is_self_message:
            # Self messages can only be deduped with origin-id
            if message_id is None:
                self._log.warning('Self message without origin-id found')
                return
            stanza_id = message_id

        if properties.mam.namespace == nbxmpp.NS_MAM_1:
            if app.logger.search_for_duplicate(
                    self._account, with_, properties.mam.timestamp, msgtxt):
                self._log.info('Found duplicate with fallback for mam:1')
                return

        app.logger.insert_into_logs(self._account,
                                    with_,
                                    properties.mam.timestamp,
                                    kind,
                                    unread=False,
                                    message=msgtxt,
                                    contact_name=properties.muc_nickname,
                                    additional_data=additional_data,
                                    stanza_id=stanza_id,
                                    message_id=properties.id)

        app.nec.push_incoming_event(
            NetworkEvent('mam-decrypted-message-received',
                         account=self._account,
                         additional_data=additional_data,
                         correct_id=parse_correction(properties),
                         archive_jid=properties.mam.archive,
                         msgtxt=properties.body,
                         properties=properties,
                         kind=kind,
                         )
        )

    def _is_valid_request(self, properties):
        valid_id = self._mam_query_ids.get(str(properties.mam.archive), None)
        return valid_id == properties.mam.query_id

    def _get_query_id(self, jid):
        query_id = self._con.connection.getAnID()
        self._mam_query_ids[jid] = query_id
        return query_id

    def _parse_iq(self, stanza):
        if not nbxmpp.isResultNode(stanza):
            self._log.error('Error on MAM query: %s', stanza.getError())
            raise InvalidMamIQ

        fin = stanza.getTag('fin')
        if fin is None:
            self._log.error('Malformed MAM query result received: %s', stanza)
            raise InvalidMamIQ

        set_ = fin.getTag('set', namespace=nbxmpp.NS_RSM)
        if set_ is None:
            self._log.error(
                'Malformed MAM query result received (no "set" Node): %s',
                stanza)
            raise InvalidMamIQ
        return fin, set_

    def _get_from_jid(self, stanza):
        jid = stanza.getFrom()
        if jid is None:
            # No from means, iq from our own archive
            jid = self._con.get_own_jid().getStripped()
        else:
            jid = jid.getStripped()
        return jid

    def request_archive_count(self, start_date, end_date):
        jid = self._con.get_own_jid().getStripped()
        self._log.info('Request archive count from: %s', jid)
        query_id = self._get_query_id(jid)
        query = self._get_archive_query(
            query_id, start=start_date, end=end_date, max_=0)
        self._con.connection.SendAndCallForResponse(
            query, self._received_count, {'query_id': query_id})
        return query_id

    def _received_count(self, _con, stanza, query_id):
        try:
            _, set_ = self._parse_iq(stanza)
        except InvalidMamIQ:
            return

        jid = self._get_from_jid(stanza)
        self._mam_query_ids.pop(jid)

        count = set_.getTagData('count')
        self._log.info('Received archive count: %s', count)
        app.nec.push_incoming_event(ArchivingCountReceived(
            None, query_id=query_id, count=count))

    def request_archive_on_signin(self):
        own_jid = self._con.get_own_jid().getStripped()

        if own_jid in self._mam_query_ids:
            self._log.warning('MAM request for %s already running', own_jid)
            return

        archive = app.logger.get_archive_infos(own_jid)

        # Migration of last_mam_id from config to DB
        if archive is not None:
            mam_id = archive.last_mam_id
        else:
            mam_id = app.config.get_per(
                'accounts', self._account, 'last_mam_id')
            if mam_id:
                app.config.del_per('accounts', self._account, 'last_mam_id')

        start_date = None
        query_id = self._get_query_id(own_jid)
        if mam_id:
            self._log.info('MAM query after: %s', mam_id)
            query = self._get_archive_query(query_id, after=mam_id)
        else:
            # First Start, we request the last week
            start_date = datetime.utcnow() - timedelta(days=7)
            self._log.info('First start: query archive start: %s', start_date)
            query = self._get_archive_query(query_id, start=start_date)

        if own_jid in self._catch_up_finished:
            self._catch_up_finished.remove(own_jid)
        self._send_archive_query(query, query_id, start_date)

    def request_archive_on_muc_join(self, jid):
        archive = app.logger.get_archive_infos(jid)
        threshold = get_sync_threshold(jid, archive)
        self._log.info('Threshold for %s: %s', jid, threshold)
        query_id = self._get_query_id(jid)
        start_date = None
        if archive is None or archive.last_mam_id is None:
            # First Start, we dont request history
            # Depending on what a MUC saves, there could be thousands
            # of Messages even in just one day.
            start_date = datetime.utcnow() - timedelta(days=1)
            self._log.info('First join: query archive %s from: %s',
                           jid, start_date)
            query = self._get_archive_query(
                query_id, jid=jid, start=start_date)

        elif threshold == SyncThreshold.NO_THRESHOLD:
            # Not our first join and no threshold set
            self._log.info('Request from archive: %s, after mam-id %s',
                           jid, archive.last_mam_id)
            query = self._get_archive_query(
                query_id, jid=jid, after=archive.last_mam_id)

        else:
            # Not our first join, check how much time elapsed since our
            # last join and check against threshold
            last_timestamp = archive.last_muc_timestamp
            if last_timestamp is None:
                self._log.info('No last muc timestamp found ( mam:1? )')
                last_timestamp = 0

            last = datetime.utcfromtimestamp(float(last_timestamp))
            if datetime.utcnow() - last > timedelta(days=threshold):
                # To much time has elapsed since last join, apply threshold
                start_date = datetime.utcnow() - timedelta(days=threshold)
                self._log.info('Too much time elapsed since last join, '
                               'request from: %s, threshold: %s',
                               start_date, threshold)
                query = self._get_archive_query(
                    query_id, jid=jid, start=start_date)
            else:
                # Request from last mam-id
                self._log.info('Request from archive %s after %s:',
                               jid, archive.last_mam_id)
                query = self._get_archive_query(
                    query_id, jid=jid, after=archive.last_mam_id)

        if jid in self._catch_up_finished:
            self._catch_up_finished.remove(jid)
        self._send_archive_query(query, query_id, start_date, groupchat=True)

    def _send_archive_query(self, query, query_id, start_date=None,
                            groupchat=False):
        self._con.connection.SendAndCallForResponse(
            query, self._result_finished, {'query_id': query_id,
                                           'start_date': start_date,
                                           'groupchat': groupchat})

    def _result_finished(self, _con, stanza, query_id, start_date, groupchat):
        try:
            fin, set_ = self._parse_iq(stanza)
        except InvalidMamIQ:
            return

        jid = self._get_from_jid(stanza)

        last = set_.getTagData('last')
        if last is None:
            self._log.info('End of MAM query, no items retrieved')
            self._catch_up_finished.append(jid)
            self._mam_query_ids.pop(jid)
            return

        complete = fin.getAttr('complete')
        if complete != 'true':
            app.logger.set_archive_infos(jid, last_mam_id=last)
            self._mam_query_ids.pop(jid)
            query_id = self._get_query_id(jid)
            query = self._get_archive_query(query_id, jid=jid, after=last)
            self._send_archive_query(query, query_id, groupchat=groupchat)
        else:
            self._mam_query_ids.pop(jid)
            app.logger.set_archive_infos(
                jid, last_mam_id=last, last_muc_timestamp=time.time())
            if start_date is not None and not groupchat:
                # Record the earliest timestamp we request from
                # the account archive. For the account archive we only
                # set start_date at the very first request.
                app.logger.set_archive_infos(
                    jid, oldest_mam_timestamp=start_date.timestamp())

            self._catch_up_finished.append(jid)
            self._log.info('End of MAM query, last mam id: %s', last)

    def request_archive_interval(self, start_date, end_date, after=None,
                                 query_id=None):
        jid = self._con.get_own_jid().getStripped()
        if after is None:
            self._log.info('Request intervall from %s to %s from %s',
                           start_date, end_date, jid)
        else:
            self._log.info('Query page after %s from %s', after, jid)
        if query_id is None:
            query_id = self._get_query_id(jid)
        self._mam_query_ids[jid] = query_id
        query = self._get_archive_query(query_id, start=start_date,
                                        end=end_date, after=after, max_=30)

        self._con.connection.SendAndCallForResponse(
            query, self._intervall_result, {'query_id': query_id,
                                            'start_date': start_date,
                                            'end_date': end_date})
        return query_id

    def _intervall_result(self, _con, stanza, query_id,
                          start_date, end_date):
        try:
            fin, set_ = self._parse_iq(stanza)
        except InvalidMamIQ:
            return

        jid = self._get_from_jid(stanza)
        self._mam_query_ids.pop(jid)
        if start_date:
            timestamp = start_date.timestamp()
        else:
            timestamp = ArchiveState.ALL

        last = set_.getTagData('last')
        if last is None:
            app.nec.push_incoming_event(ArchivingIntervalFinished(
                None, query_id=query_id))
            app.logger.set_archive_infos(
                jid, oldest_mam_timestamp=timestamp)
            self._log.info('End of MAM request, no items retrieved')
            return

        complete = fin.getAttr('complete')
        if complete != 'true':
            self.request_archive_interval(start_date, end_date, last, query_id)
        else:
            self._log.info('Request finished')
            app.logger.set_archive_infos(
                jid, oldest_mam_timestamp=timestamp)
            app.nec.push_incoming_event(ArchivingIntervalFinished(
                None, query_id=query_id))

    def _get_archive_query(self, query_id, jid=None, start=None, end=None,
                           with_=None, after=None, max_=70):
        # Muc archive query?
        disco_info = app.logger.get_last_disco_info(jid)
        if disco_info is None:
            # Query to our own archive
            namespace = self.archiving_namespace
        else:
            namespace = disco_info.mam_namespace

        iq = nbxmpp.Iq('set', to=jid)
        query = iq.addChild('query', namespace=namespace)
        form = query.addChild(node=nbxmpp.DataForm(typ='submit'))
        field = nbxmpp.DataField(typ='hidden',
                                 name='FORM_TYPE',
                                 value=namespace)
        form.addChild(node=field)
        if start:
            field = nbxmpp.DataField(
                typ='text-single',
                name='start',
                value=start.strftime('%Y-%m-%dT%H:%M:%SZ'))
            form.addChild(node=field)
        if end:
            field = nbxmpp.DataField(typ='text-single',
                                     name='end',
                                     value=end.strftime('%Y-%m-%dT%H:%M:%SZ'))
            form.addChild(node=field)
        if with_:
            field = nbxmpp.DataField(typ='jid-single',
                                     name='with',
                                     value=with_)
            form.addChild(node=field)

        set_ = query.setTag('set', namespace=nbxmpp.NS_RSM)
        set_.setTagData('max', max_)
        if after:
            set_.setTagData('after', after)
        query.setAttr('queryid', query_id)
        return iq

    def request_mam_preferences(self):
        self._log.info('Request MAM preferences')
        iq = nbxmpp.Iq('get', self.archiving_namespace)
        iq.setQuery('prefs')
        self._con.connection.SendAndCallForResponse(
            iq, self._preferences_received)

    def _preferences_received(self, stanza):
        if not nbxmpp.isResultNode(stanza):
            self._log.info('Error: %s', stanza.getError())
            app.nec.push_incoming_event(MAMPreferenceError(
                None, conn=self._con, error=stanza.getError()))
            return

        self._log.info('Received MAM preferences')
        prefs = stanza.getTag('prefs', namespace=self.archiving_namespace)
        if prefs is None:
            self._log.error('Malformed stanza (no prefs node): %s', stanza)
            return

        rules = []
        default = prefs.getAttr('default')
        for item in prefs.getTag('always').getTags('jid'):
            rules.append((item.getData(), 'Always'))

        for item in prefs.getTag('never').getTags('jid'):
            rules.append((item.getData(), 'Never'))

        app.nec.push_incoming_event(MAMPreferenceReceived(
            None, conn=self._con, rules=rules, default=default))

    def set_mam_preferences(self, rules, default):
        iq = nbxmpp.Iq(typ='set')
        prefs = iq.addChild(name='prefs',
                            namespace=self.archiving_namespace,
                            attrs={'default': default})
        always = prefs.addChild(name='always')
        never = prefs.addChild(name='never')
        for item in rules:
            jid, archive = item
            if archive:
                always.addChild(name='jid').setData(jid)
            else:
                never.addChild(name='jid').setData(jid)

        self._con.connection.SendAndCallForResponse(
            iq, self._preferences_saved)

    def _preferences_saved(self, stanza):
        if not nbxmpp.isResultNode(stanza):
            self._log.info('Error: %s', stanza.getError())
            app.nec.push_incoming_event(MAMPreferenceError(
                None, conn=self._con, error=stanza.getError()))
        else:
            self._log.info('Preferences saved')
            app.nec.push_incoming_event(
                MAMPreferenceSaved(None, conn=self._con))


class MAMPreferenceError(NetworkIncomingEvent):
    name = 'mam-prefs-error'


class MAMPreferenceReceived(NetworkIncomingEvent):
    name = 'mam-prefs-received'


class MAMPreferenceSaved(NetworkIncomingEvent):
    name = 'mam-prefs-saved'


class ArchivingCountReceived(NetworkIncomingEvent):
    name = 'archiving-count-received'


class ArchivingIntervalFinished(NetworkIncomingEvent):
    name = 'archiving-interval-finished'


class ArchivingErrorReceived(NetworkIncomingEvent):
    name = 'archiving-error-received'


class InvalidMamIQ(Exception):
    pass


def get_instance(*args, **kwargs):
    return MAM(*args, **kwargs), 'MAM'
