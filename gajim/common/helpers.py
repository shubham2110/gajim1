# Copyright (C) 2003-2014 Yann Leboulanger <asterix AT lagaule.org>
# Copyright (C) 2005-2006 Dimitur Kirov <dkirov AT gmail.com>
#                         Nikos Kouremenos <kourem AT gmail.com>
# Copyright (C) 2006 Alex Mauer <hawke AT hawkesnest.net>
# Copyright (C) 2006-2007 Travis Shirk <travis AT pobox.com>
# Copyright (C) 2006-2008 Jean-Marie Traissard <jim AT lapin.org>
# Copyright (C) 2007 Lukas Petrovicky <lukas AT petrovicky.net>
#                    James Newton <redshodan AT gmail.com>
#                    Julien Pivotto <roidelapluie AT gmail.com>
# Copyright (C) 2007-2008 Stephan Erb <steve-e AT h3c.de>
# Copyright (C) 2008 Brendan Taylor <whateley AT gmail.com>
#                    Jonathan Schleifer <js-gajim AT webkeks.org>
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

from typing import Any  # pylint: disable=unused-import
from typing import Dict  # pylint: disable=unused-import

import sys
import re
import os
import subprocess
import webbrowser
import errno
import select
import base64
import hashlib
import shlex
import socket
import time
import logging
import json
import shutil
import collections
from collections import defaultdict
import random
import weakref
import string
from string import Template
import urllib
from urllib.parse import unquote
from io import StringIO
from datetime import datetime, timedelta
from distutils.version import LooseVersion as V
from encodings.punycode import punycode_encode
from functools import wraps

import nbxmpp
from nbxmpp.util import compute_caps_hash
from nbxmpp.stringprepare import nameprep
from nbxmpp.structs import DiscoInfo
from nbxmpp.const import Role
from nbxmpp.protocol import JID
from nbxmpp.protocol import InvalidJid
from gi.repository import Gio
from gi.repository import GLib
import precis_i18n.codec  # pylint: disable=unused-import

from gajim.common import app
from gajim.common import configpaths
from gajim.common.i18n import Q_
from gajim.common.i18n import _
from gajim.common.i18n import ngettext
from gajim.common.i18n import get_rfc5646_lang
from gajim.common.const import ShowConstant
from gajim.common.const import Display
from gajim.common.const import URIType
from gajim.common.const import URIAction
from gajim.common.const import GIO_TLS_ERRORS
from gajim.common.structs import URI

if app.is_installed('PYCURL'):
    import pycurl


log = logging.getLogger('gajim.c.helpers')

special_groups = (_('Transports'), _('Not in contact list'), _('Observers'), _('Group chats'))

URL_REGEX = re.compile(
    r"(www\.(?!\.)|[a-z][a-z0-9+.-]*://)[^\s<>'\"]+[^!,\.\s<>\)'\"\]]")


class InvalidFormat(Exception):
    pass


def decompose_jid(jidstring):
    user = None
    server = None
    resource = None

    # Search for delimiters
    user_sep = jidstring.find('@')
    res_sep = jidstring.find('/')

    if user_sep == -1:
        if res_sep == -1:
            # host
            server = jidstring
        else:
            # host/resource
            server = jidstring[0:res_sep]
            resource = jidstring[res_sep + 1:]
    else:
        if res_sep == -1:
            # user@host
            user = jidstring[0:user_sep]
            server = jidstring[user_sep + 1:]
        else:
            if user_sep < res_sep:
                # user@host/resource
                user = jidstring[0:user_sep]
                server = jidstring[user_sep + 1:user_sep + (res_sep - user_sep)]
                resource = jidstring[res_sep + 1:]
            else:
                # server/resource (with an @ in resource)
                server = jidstring[0:res_sep]
                resource = jidstring[res_sep + 1:]
    return user, server, resource

def parse_jid(jidstring):
    """
    Perform stringprep on all JID fragments from a string and return the full
    jid
    """
    # This function comes from http://svn.twistedmatrix.com/cvs/trunk/twisted/words/protocols/jabber/jid.py

    return prep(*decompose_jid(jidstring))

def idn_to_ascii(host):
    """
    Convert IDN (Internationalized Domain Names) to ACE (ASCII-compatible
    encoding)
    """
    from encodings import idna
    labels = idna.dots.split(host)
    converted_labels = []
    for label in labels:
        if label:
            converted_labels.append(idna.ToASCII(label).decode('utf-8'))
        else:
            converted_labels.append('')
    return ".".join(converted_labels)

def ascii_to_idn(host):
    """
    Convert ACE (ASCII-compatible encoding) to IDN (Internationalized Domain
    Names)
    """
    from encodings import idna
    labels = idna.dots.split(host)
    converted_labels = []
    for label in labels:
        converted_labels.append(idna.ToUnicode(label))
    return ".".join(converted_labels)

def puny_encode_url(url):
    _url = url
    if '//' not in _url:
        _url = '//' + _url
    try:
        o = urllib.parse.urlparse(_url)
        p_loc = idn_to_ascii(o.netloc)
    except Exception:
        log.debug('urlparse failed: %s', url)
        return False
    return url.replace(o.netloc, p_loc)

def parse_resource(resource):
    """
    Perform stringprep on resource and return it
    """
    if resource:
        try:
            return resource.encode('OpaqueString').decode('utf-8')
        except UnicodeError:
            raise InvalidFormat('Invalid character in resource.')

def prep(user, server, resource):
    """
    Perform stringprep on all JID fragments and return the full jid
    """
    # This function comes from
    #http://svn.twistedmatrix.com/cvs/trunk/twisted/words/protocols/jabber/jid.py

    ip_address = False

    try:
        socket.inet_aton(server)
        ip_address = True
    except socket.error:
        pass

    if not ip_address and hasattr(socket, 'inet_pton'):
        try:
            socket.inet_pton(socket.AF_INET6, server.strip('[]'))
            server = '[%s]' % server.strip('[]')
            ip_address = True
        except (socket.error, ValueError):
            pass

    if not ip_address:
        if server is not None:
            if server.endswith('.'):  # RFC7622, 3.2
                server = server[:-1]
            if not server or len(server.encode('utf-8')) > 1023:
                raise InvalidFormat(_('Server must be between 1 and 1023 bytes'))
            try:
                server = nameprep.prepare(server)
            except UnicodeError:
                raise InvalidFormat(_('Invalid character in hostname.'))
        else:
            raise InvalidFormat(_('Server address required.'))

    if user is not None:
        if not user or len(user.encode('utf-8')) > 1023:
            raise InvalidFormat(_('Username must be between 1 and 1023 bytes'))
        try:
            user = user.encode('UsernameCaseMapped').decode('utf-8')
        except UnicodeError:
            raise InvalidFormat(_('Invalid character in username.'))
    else:
        user = None

    if resource is not None:
        if not resource or len(resource.encode('utf-8')) > 1023:
            raise InvalidFormat(_('Resource must be between 1 and 1023 bytes'))
        try:
            resource = resource.encode('OpaqueString').decode('utf-8')
        except UnicodeError:
            raise InvalidFormat(_('Invalid character in resource.'))
    else:
        resource = None

    if user:
        if resource:
            return '%s@%s/%s' % (user, server, resource)
        return '%s@%s' % (user, server)

    if resource:
        return '%s/%s' % (server, resource)
    return server

def windowsify(s):
    if os.name == 'nt':
        return s.capitalize()
    return s

def temp_failure_retry(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except (os.error, IOError, select.error) as ex:
            if ex.errno == errno.EINTR:
                continue
            raise

def get_uf_show(show, use_mnemonic=False):
    """
    Return a userfriendly string for dnd/xa/chat and make all strings
    translatable

    If use_mnemonic is True, it adds _ so GUI should call with True for
    accessibility issues
    """
    if isinstance(show, ShowConstant):
        show = show.name.lower()

    if show == 'dnd':
        if use_mnemonic:
            uf_show = _('_Busy')
        else:
            uf_show = _('Busy')
    elif show == 'xa':
        if use_mnemonic:
            uf_show = _('_Not Available')
        else:
            uf_show = _('Not Available')
    elif show == 'chat':
        if use_mnemonic:
            uf_show = _('_Free for Chat')
        else:
            uf_show = _('Free for Chat')
    elif show == 'online':
        if use_mnemonic:
            uf_show = Q_('?user status:_Available')
        else:
            uf_show = Q_('?user status:Available')
    elif show == 'connecting':
        uf_show = _('Connecting')
    elif show == 'away':
        if use_mnemonic:
            uf_show = _('A_way')
        else:
            uf_show = _('Away')
    elif show == 'offline':
        if use_mnemonic:
            uf_show = _('_Offline')
        else:
            uf_show = _('Offline')
    elif show == 'invisible':
        if use_mnemonic:
            uf_show = _('_Invisible')
        else:
            uf_show = _('Invisible')
    elif show == 'not in roster':
        uf_show = _('Not in contact list')
    elif show == 'requested':
        uf_show = Q_('?contact has status:Unknown')
    else:
        uf_show = Q_('?contact has status:Has errors')
    return uf_show

def get_css_show_color(show):
    if show in ('online', 'chat', 'invisible'):
        return 'status-online'
    if show in ('offline', 'not in roster', 'requested'):
        return None
    if show in ('xa', 'dnd'):
        return 'status-dnd'
    if show == 'away':
        return 'status-away'

def get_uf_sub(sub):
    if sub == 'none':
        uf_sub = Q_('?Subscription we already have:None')
    elif sub == 'to':
        uf_sub = _('To')
    elif sub == 'from':
        uf_sub = _('From')
    elif sub == 'both':
        uf_sub = _('Both')
    else:
        uf_sub = _('Unknown')

    return uf_sub

def get_uf_ask(ask):
    if ask is None:
        uf_ask = Q_('?Ask (for Subscription):None')
    elif ask == 'subscribe':
        uf_ask = _('Subscribe')
    else:
        uf_ask = ask

    return uf_ask

def get_uf_role(role, plural=False):
    ''' plural determines if you get Moderators or Moderator'''
    if not isinstance(role, str):
        role = role.value

    if role == 'none':
        role_name = Q_('?Group Chat Contact Role:None')
    elif role == 'moderator':
        if plural:
            role_name = _('Moderators')
        else:
            role_name = _('Moderator')
    elif role == 'participant':
        if plural:
            role_name = _('Participants')
        else:
            role_name = _('Participant')
    elif role == 'visitor':
        if plural:
            role_name = _('Visitors')
        else:
            role_name = _('Visitor')
    return role_name

def get_uf_affiliation(affiliation, plural=False):
    '''Get a nice and translated affilition for muc'''
    if not isinstance(affiliation, str):
        affiliation = affiliation.value

    if affiliation == 'none':
        affiliation_name = Q_('?Group Chat Contact Affiliation:None')
    elif affiliation == 'owner':
        if plural:
            affiliation_name = _('Owners')
        else:
            affiliation_name = _('Owner')
    elif affiliation == 'admin':
        if plural:
            affiliation_name = _('Administrators')
        else:
            affiliation_name = _('Administrator')
    elif affiliation == 'member':
        if plural:
            affiliation_name = _('Members')
        else:
            affiliation_name = _('Member')
    return affiliation_name

def get_sorted_keys(adict):
    keys = sorted(adict.keys())
    return keys

def to_one_line(msg):
    msg = msg.replace('\\', '\\\\')
    msg = msg.replace('\n', '\\n')
    # s1 = 'test\ntest\\ntest'
    # s11 = s1.replace('\\', '\\\\')
    # s12 = s11.replace('\n', '\\n')
    # s12
    # 'test\\ntest\\\\ntest'
    return msg

def from_one_line(msg):
    # (?<!\\) is a lookbehind assertion which asks anything but '\'
    # to match the regexp that follows it

    # So here match '\\n' but not if you have a '\' before that
    expr = re.compile(r'(?<!\\)\\n')
    msg = expr.sub('\n', msg)
    msg = msg.replace('\\\\', '\\')
    # s12 = 'test\\ntest\\\\ntest'
    # s13 = re.sub('\n', s12)
    # s14 s13.replace('\\\\', '\\')
    # s14
    # 'test\ntest\\ntest'
    return msg

def get_uf_chatstate(chatstate):
    """
    Remove chatstate jargon and returns user friendly messages
    """
    if chatstate == 'active':
        return _('is paying attention to the conversation')
    if chatstate == 'inactive':
        return _('is doing something else')
    if chatstate == 'composing':
        return _('is composing a message…')
    if chatstate == 'paused':
        #paused means he or she was composing but has stopped for a while
        return _('paused composing a message')
    if chatstate == 'gone':
        return _('has closed the chat window or tab')
    return ''

def find_soundplayer():
    if sys.platform in ('win32', 'darwin'):
        return

    if app.config.get('soundplayer') != '':
        return

    commands = ('aucat', 'paplay', 'aplay', 'play', 'ossplay')
    for command in commands:
        if shutil.which(command) is not None:
            if command == 'paplay':
                command += ' -n gajim --property=media.role=event'
            elif command in ('aplay', 'play'):
                command += ' -q'
            elif command == 'ossplay':
                command += ' -qq'
            elif command == 'aucat':
                command += ' -i'
            app.config.set('soundplayer', command)
            break

def exec_command(command, use_shell=False, posix=True):
    """
    execute a command. if use_shell is True, we run the command as is it was
    typed in a console. So it may be dangerous if you are not sure about what
    is executed.
    """
    if use_shell:
        subprocess.Popen('%s &' % command, shell=True).wait()
    else:
        args = shlex.split(command, posix=posix)
        p = subprocess.Popen(args)
        app.thread_interface(p.wait)

def build_command(executable, parameter):
    # we add to the parameter (can hold path with spaces)
    # "" so we have good parsing from shell
    parameter = parameter.replace('"', '\\"') # but first escape "
    command = '%s "%s"' % (executable, parameter)
    return command

def get_file_path_from_dnd_dropped_uri(uri):
    path = urllib.parse.unquote(uri) # escape special chars
    path = path.strip('\r\n\x00') # remove \r\n and NULL
    # get the path to file
    if re.match('^file:///[a-zA-Z]:/', path): # windows
        path = path[8:] # 8 is len('file:///')
    elif path.startswith('file://'): # nautilus, rox
        path = path[7:] # 7 is len('file://')
    elif path.startswith('file:'): # xffm
        path = path[5:] # 5 is len('file:')
    return path

def get_xmpp_show(show):
    if show in ('online', 'offline'):
        return None
    return show

def sanitize_filename(filename):
    """
    Make sure the filename we will write does contain only acceptable and latin
    characters, and is not too long (in that case hash it)
    """
    # 48 is the limit
    if len(filename) > 48:
        hash_ = hashlib.md5(filename.encode('utf-8'))
        filename = base64.b64encode(hash_.digest()).decode('utf-8')

    # make it latin chars only
    filename = punycode_encode(filename).decode('utf-8')
    filename = filename.replace('/', '_')
    if os.name == 'nt':
        filename = filename.replace('?', '_').replace(':', '_')\
                .replace('\\', '_').replace('"', "'").replace('|', '_')\
                .replace('*', '_').replace('<', '_').replace('>', '_')

    return filename

def reduce_chars_newlines(text, max_chars=0, max_lines=0):
    """
    Cut the chars after 'max_chars' on each line and show only the first
    'max_lines'

    If any of the params is not present (None or 0) the action on it is not
    performed
    """
    def _cut_if_long(string_):
        if len(string_) > max_chars:
            string_ = string_[:max_chars - 3] + '…'
        return string_

    if max_lines == 0:
        lines = text.split('\n')
    else:
        lines = text.split('\n', max_lines)[:max_lines]
    if max_chars > 0:
        if lines:
            lines = [_cut_if_long(e) for e in lines]
    if lines:
        reduced_text = '\n'.join(lines)
        if reduced_text != text:
            reduced_text += '…'
    else:
        reduced_text = ''
    return reduced_text

def get_account_status(account):
    status = reduce_chars_newlines(account['status_line'], 100, 1)
    return status

def datetime_tuple(timestamp):
    """
    Convert timestamp using strptime and the format: %Y%m%dT%H:%M:%S

    Because of various datetime formats are used the following exceptions
    are handled:
            - Optional milliseconds appened to the string are removed
            - Optional Z (that means UTC) appened to the string are removed
            - XEP-082 datetime strings have all '-' cahrs removed to meet
              the above format.
    """
    date, tim = timestamp.split('T', 1)
    date = date.replace('-', '')
    tim = tim.replace('z', '')
    tim = tim.replace('Z', '')
    zone = None
    if '+' in tim:
        sign = -1
        tim, zone = tim.split('+', 1)
    if '-' in tim:
        sign = 1
        tim, zone = tim.split('-', 1)
    tim = tim.split('.')[0]
    tim = time.strptime(date + 'T' + tim, '%Y%m%dT%H:%M:%S')
    if zone:
        zone = zone.replace(':', '')
        tim = datetime.fromtimestamp(time.mktime(tim))
        if len(zone) > 2:
            zone = time.strptime(zone, '%H%M')
        else:
            zone = time.strptime(zone, '%H')
        zone = timedelta(hours=zone.tm_hour, minutes=zone.tm_min)
        tim += zone * sign
        tim = tim.timetuple()
    return tim

def get_contact_dict_for_account(account):
    """
    Create a dict of jid, nick -> contact with all contacts of account.

    Can be used for completion lists
    """
    contacts_dict = {}
    for jid in app.contacts.get_jid_list(account):
        contact = app.contacts.get_contact_with_highest_priority(account,
                        jid)
        contacts_dict[jid] = contact
        name = contact.name
        if name in contacts_dict:
            contact1 = contacts_dict[name]
            del contacts_dict[name]
            contacts_dict['%s (%s)' % (name, contact1.jid)] = contact1
            contacts_dict['%s (%s)' % (name, jid)] = contact
        elif contact.name:
            if contact.name == app.get_nick_from_jid(jid):
                del contacts_dict[jid]
            contacts_dict[name] = contact
    return contacts_dict

def play_sound(event):
    if not app.config.get('sounds_on'):
        return
    path_to_soundfile = app.config.get_per('soundevents', event, 'path')
    play_sound_file(path_to_soundfile)

def check_soundfile_path(file_, dirs=None):
    """
    Check if the sound file exists

    :param file_: the file to check, absolute or relative to 'dirs' path
    :param dirs: list of knows paths to fallback if the file doesn't exists
                                     (eg: ~/.gajim/sounds/, DATADIR/sounds...).
    :return      the path to file or None if it doesn't exists.
    """
    if dirs is None:
        dirs = [configpaths.get('MY_DATA'),
                configpaths.get('DATA')]

    if not file_:
        return None
    if os.path.exists(file_):
        return file_

    for d in dirs:
        d = os.path.join(d, 'sounds', file_)
        if os.path.exists(d):
            return d
    return None

def strip_soundfile_path(file_, dirs=None, abs_=True):
    """
    Remove knowns paths from a sound file

    Filechooser returns absolute path. If path is a known fallback path, we remove it.
    So config have no hardcoded path        to DATA_DIR and text in textfield is shorther.
    param: file_: the filename to strip.
    param: dirs: list of knowns paths from which the filename should be stripped.
    param:  abs_: force absolute path on dirs
    """
    if not file_:
        return None

    if dirs is None:
        dirs = [configpaths.get('MY_DATA'),
                configpaths.get('DATA')]

    name = os.path.basename(file_)
    for d in dirs:
        d = os.path.join(d, 'sounds', name)
        if abs_:
            d = os.path.abspath(d)
        if file_ == d:
            return name
    return file_

def play_sound_file(path_to_soundfile):
    path_to_soundfile = check_soundfile_path(path_to_soundfile)
    if path_to_soundfile is None:
        return

    if sys.platform == 'win32':
        import winsound
        try:
            winsound.PlaySound(path_to_soundfile,
                               winsound.SND_FILENAME|winsound.SND_ASYNC)
        except Exception:
            log.exception('Sound Playback Error')

    elif sys.platform == 'darwin':
        try:
            from AppKit import NSSound
        except ImportError:
            log.exception('Sound Playback Error')
            return

        sound = NSSound.alloc()
        sound.initWithContentsOfFile_byReference_(path_to_soundfile, True)
        sound.play()

    elif app.config.get('soundplayer') == '':
        try:
            import wave
            import ossaudiodev
        except Exception:
            log.exception('Sound Playback Error')
            return

        def _oss_play():
            sndfile = wave.open(path_to_soundfile, 'rb')
            nc, sw, fr, nf, _comptype, _compname = sndfile.getparams()
            dev = ossaudiodev.open('/dev/dsp', 'w')
            dev.setparameters(sw * 8, nc, fr)
            dev.write(sndfile.readframes(nf))
            sndfile.close()
            dev.close()
        app.thread_interface(_oss_play)

    else:
        player = app.config.get('soundplayer')
        command = build_command(player, path_to_soundfile)
        exec_command(command)

def get_global_show():
    maxi = 0
    for account in app.connections:
        if not app.config.get_per('accounts', account,
        'sync_with_global_status'):
            continue
        connected = app.connections[account].connected
        if connected > maxi:
            maxi = connected
    return app.SHOW_LIST[maxi]

def get_global_status():
    maxi = 0
    for account in app.connections:
        if not app.config.get_per('accounts', account,
        'sync_with_global_status'):
            continue
        connected = app.connections[account].connected
        if connected > maxi:
            maxi = connected
            status = app.connections[account].status
    return status


def statuses_unified():
    """
    Test if all statuses are the same
    """
    reference = None
    for account in app.connections:
        if not app.config.get_per('accounts', account,
        'sync_with_global_status'):
            continue
        if reference is None:
            reference = app.connections[account].connected
        elif reference != app.connections[account].connected:
            return False
    return True

def get_icon_name_to_show(contact, account=None):
    """
    Get the icon name to show in online, away, requested, etc
    """
    if account and app.events.get_nb_roster_events(account, contact.jid):
        return 'event'
    if account and app.events.get_nb_roster_events(
        account, contact.get_full_jid()):
        return 'event'
    if account and account in app.interface.minimized_controls and \
    contact.jid in app.interface.minimized_controls[account] and app.interface.\
            minimized_controls[account][contact.jid].get_nb_unread_pm() > 0:
        return 'event'
    if account and contact.jid in app.gc_connected[account]:
        if app.gc_connected[account][contact.jid]:
            return 'muc-active'
        return 'muc-inactive'
    if contact.jid.find('@') <= 0: # if not '@' or '@' starts the jid ==> agent
        return contact.show
    if contact.sub in ('both', 'to'):
        return contact.show
    if contact.ask == 'subscribe':
        return 'requested'
    transport = app.get_transport_name_from_jid(contact.jid)
    if transport:
        return contact.show
    if contact.show in app.SHOW_LIST:
        return contact.show
    return 'notinroster'

def get_full_jid_from_iq(iq_obj):
    """
    Return the full jid (with resource) from an iq
    """
    jid = iq_obj.getFrom()
    if jid is None:
        return None
    return parse_jid(str(iq_obj.getFrom()))

def get_jid_from_iq(iq_obj):
    """
    Return the jid (without resource) from an iq
    """
    jid = get_full_jid_from_iq(iq_obj)
    return app.get_jid_without_resource(jid)

def get_auth_sha(sid, initiator, target):
    """
    Return sha of sid + initiator + target used for proxy auth
    """
    return hashlib.sha1(("%s%s%s" % (sid, initiator, target)).encode('utf-8')).\
        hexdigest()

def remove_invalid_xml_chars(string_):
    if string_:
        string_ = re.sub(app.interface.invalid_XML_chars_re, '', string_)
    return string_

def get_random_string_16():
    """
    Create random string of length 16
    """
    rng = list(range(65, 90))
    rng.extend(range(48, 57))
    char_sequence = [chr(e) for e in rng]
    from random import sample
    return ''.join(sample(char_sequence, 16))

def get_os_info():
    if app.os_info:
        return app.os_info
    app.os_info = 'N/A'
    if os.name == 'nt' or sys.platform == 'darwin':
        import platform
        app.os_info = platform.system() + " " + platform.release()
    elif os.name == 'posix':
        try:
            import distro
            app.os_info = distro.name(pretty=True)
        except ImportError:
            import platform
            app.os_info = platform.system()
    return app.os_info

def allow_showing_notification(account, type_='notify_on_new_message',
is_first_message=True):
    """
    Is it allowed to show nofication?

    Check OUR status and if we allow notifications for that status type is the
    option that need to be True e.g.: notify_on_signing is_first_message: set it
    to false when it's not the first message
    """
    if type_ and (not app.config.get(type_) or not is_first_message):
        return False
    if app.config.get('autopopupaway'): # always show notification
        return True
    if app.connections[account].connected in (2, 3): # we're online or chat
        return True
    return False

def allow_popup_window(account):
    """
    Is it allowed to popup windows?
    """
    autopopup = app.config.get('autopopup')
    autopopupaway = app.config.get('autopopupaway')
    if autopopup and (autopopupaway or \
    app.connections[account].connected in (2, 3)): # we're online or chat
        return True
    return False

def allow_sound_notification(account, sound_event):
    if app.config.get('sounddnd') or app.connections[account].connected != \
    app.SHOW_LIST.index('dnd') and app.config.get_per('soundevents',
    sound_event, 'enabled'):
        return True
    return False

def get_chat_control(account, contact):
    full_jid_with_resource = contact.jid
    if contact.resource:
        full_jid_with_resource += '/' + contact.resource
    highest_contact = app.contacts.get_contact_with_highest_priority(
        account, contact.jid)

    # Look for a chat control that has the given resource, or default to
    # one without resource
    ctrl = app.interface.msg_win_mgr.get_control(full_jid_with_resource,
            account)

    if ctrl:
        return ctrl

    if (highest_contact and
        highest_contact.resource and
            contact.resource != highest_contact.resource):
        return None

    # unknown contact or offline message
    return app.interface.msg_win_mgr.get_control(contact.jid, account)

def get_notification_icon_tooltip_dict():
    """
    Return a dict of the form {acct: {'show': show, 'message': message,
    'event_lines': [list of text lines to show in tooltip]}
    """
    # How many events must there be before they're shown summarized, not per-user
    max_ungrouped_events = 10

    accounts = get_accounts_info()

    # Gather events. (With accounts, when there are more.)
    for account in accounts:
        account_name = account['name']
        account['event_lines'] = []
        # Gather events per-account
        pending_events = app.events.get_events(account=account_name)
        messages, non_messages, total_messages, total_non_messages = {}, {}, 0, 0
        for jid in pending_events:
            for event in pending_events[jid]:
                if event.type_.count('file') > 0:
                    # This is a non-messagee event.
                    messages[jid] = non_messages.get(jid, 0) + 1
                    total_non_messages = total_non_messages + 1
                else:
                    # This is a message.
                    messages[jid] = messages.get(jid, 0) + 1
                    total_messages = total_messages + 1
        # Display unread messages numbers, if any
        if total_messages > 0:
            if total_messages > max_ungrouped_events:
                text = ngettext(
                        '%d message pending',
                        '%d messages pending',
                        total_messages, total_messages, total_messages)
                account['event_lines'].append(text)
            else:
                for jid in messages:
                    text = ngettext(
                            '%d message pending',
                            '%d messages pending',
                            messages[jid], messages[jid], messages[jid])
                    contact = app.contacts.get_first_contact_from_jid(
                            account['name'], jid)
                    text += ' '
                    if jid in app.gc_connected[account['name']]:
                        text += _('from group chat %s') % (jid)
                    elif contact:
                        name = contact.get_shown_name()
                        text += _('from user %s') % (name)
                    else:
                        text += _('from %s') % (jid)
                    account['event_lines'].append(text)

        # Display unseen events numbers, if any
        if total_non_messages > 0:
            if total_non_messages > max_ungrouped_events:
                text = ngettext(
                    '%d event pending',
                    '%d events pending',
                    total_non_messages, total_non_messages, total_non_messages)
                account['event_lines'].append(text)
            else:
                for jid in non_messages:
                    text = ngettext('%d event pending', '%d events pending',
                        non_messages[jid], non_messages[jid], non_messages[jid])
                    text += ' ' + _('from user %s') % (jid)
                    account[account]['event_lines'].append(text)

    return accounts

def get_notification_icon_tooltip_text():
    text = None
    # How many events must there be before they're shown summarized, not per-user
    # max_ungrouped_events = 10
    # Character which should be used to indent in the tooltip.
    indent_with = ' '

    accounts = get_notification_icon_tooltip_dict()

    if not accounts:
        # No configured account
        return _('Gajim')

    # at least one account present

    # Is there more that one account?
    if len(accounts) == 1:
        show_more_accounts = False
    else:
        show_more_accounts = True

    # If there is only one account, its status is shown on the first line.
    if show_more_accounts:
        text = _('Gajim')
    else:
        text = _('Gajim - %s') % (get_account_status(accounts[0]))

    # Gather and display events. (With accounts, when there are more.)
    for account in accounts:
        account_name = account['name']
        # Set account status, if not set above
        if show_more_accounts:
            message = '\n' + indent_with + ' %s - %s'
            text += message % (account_name, get_account_status(account))
            # Account list shown, messages need to be indented more
            indent_how = 2
        else:
            # If no account list is shown, messages could have default indenting.
            indent_how = 1
        for line in account['event_lines']:
            text += '\n' + indent_with * indent_how + ' '
            text += line
    return text

def get_accounts_info():
    """
    Helper for notification icon tooltip
    """
    accounts = []
    accounts_list = sorted(app.contacts.get_accounts())
    for account in accounts_list:
        status_idx = app.connections[account].connected
        # uncomment the following to hide offline accounts
        # if status_idx == 0: continue
        status = app.SHOW_LIST[status_idx]
        message = app.connections[account].status
        single_line = get_uf_show(status)
        if message is None:
            message = ''
        else:
            message = message.strip()
        if message != '':
            single_line += ': ' + message
        account_label = app.get_account_label(account)
        accounts.append({'name': account,
                         'account_label': account_label,
                         'status_line': single_line,
                         'show': status,
                         'message': message})
    return accounts

def get_current_show(account):
    if account not in app.connections:
        return 'offline'
    status = app.connections[account].connected
    return app.SHOW_LIST[status]

def update_optional_features(account=None):
    if account is not None:
        accounts = [account]
    else:
        accounts = app.connections.keys()

    for account_ in accounts:
        features = []
        app.gajim_optional_features[account_] = features
        if app.config.get_per('accounts', account_, 'subscribe_mood'):
            features.append(nbxmpp.NS_MOOD + '+notify')
        if app.config.get_per('accounts', account_, 'subscribe_activity'):
            features.append(nbxmpp.NS_ACTIVITY + '+notify')
        if app.config.get_per('accounts', account_, 'subscribe_tune'):
            features.append(nbxmpp.NS_TUNE + '+notify')
        if app.config.get_per('accounts', account_, 'subscribe_nick'):
            features.append(nbxmpp.NS_NICK + '+notify')
        if app.config.get_per('accounts', account_, 'subscribe_location'):
            features.append(nbxmpp.NS_LOCATION + '+notify')
        if app.connections[account_].get_module('Bookmarks').using_bookmark_2:
            features.append(nbxmpp.NS_BOOKMARKS_2 + '+notify')
        elif app.connections[account_].get_module('Bookmarks').using_bookmark_1:
            features.append(nbxmpp.NS_BOOKMARKS + '+notify')
        if app.is_installed('FARSTREAM'):
            features.append(nbxmpp.NS_JINGLE_RTP)
            features.append(nbxmpp.NS_JINGLE_RTP_AUDIO)
            features.append(nbxmpp.NS_JINGLE_RTP_VIDEO)
            features.append(nbxmpp.NS_JINGLE_ICE_UDP)

        # Give plugins the possibility to add their features
        app.plugin_manager.extension_point('update_caps', account_)

        disco_info = DiscoInfo(None,
                               [app.gajim_identity],
                               app.gajim_common_features + features,
                               [])
        app.caps_hash[account_] = compute_caps_hash(disco_info, compare=False)
        # re-send presence with new hash
        connected = app.connections[account_].connected
        if connected > 1 and app.SHOW_LIST[connected] != 'invisible':
            app.connections[account_].change_status(
                app.SHOW_LIST[connected], app.connections[account_].status)

def jid_is_blocked(account, jid):
    con = app.connections[account]
    return (jid in con.get_module('Blocking').blocked or
            jid in con.get_module('PrivacyLists').blocked_contacts or
            con.get_module('PrivacyLists').blocked_all)

def group_is_blocked(account, group):
    con = app.connections[account]
    return (group in con.get_module('PrivacyLists').blocked_groups or
            con.get_module('PrivacyLists').blocked_all)

def get_subscription_request_msg(account=None):
    s = app.config.get_per('accounts', account, 'subscription_request_msg')
    if s:
        return s
    s = _('I would like to add you to my contact list.')
    if account:
        s = _('Hello, I am $name.') + ' ' + s
        name = app.connections[account].get_module('VCardTemp').get_vard_name()
        nick = app.nicks[account]
        if name and nick:
            name += ' (%s)' % nick
        elif nick:
            name = nick
        s = Template(s).safe_substitute({'name': name})
        return s

def replace_dataform_media(form, stanza):
    found = False
    for field in form.getTags('field'):
        for media in field.getTags('media'):
            for uri in media.getTags('uri'):
                uri_data = uri.getData()
                if uri_data.startswith('cid:'):
                    uri_data = uri_data[4:]
                    for data in stanza.getTags('data', namespace=nbxmpp.NS_BOB):
                        if data.getAttr('cid') == uri_data:
                            uri.setData(data.getData())
                            found = True
    return found

def get_proxy_info(account):
    p = app.config.get_per('accounts', account, 'proxy')
    if not p:
        if app.config.get_per('accounts', account, 'use_env_http_proxy'):
            try:
                try:
                    env_http_proxy = os.environ['HTTP_PROXY']
                except Exception:
                    env_http_proxy = os.environ['http_proxy']
                env_http_proxy = env_http_proxy.strip('"')
                # Dispose of the http:// prefix
                env_http_proxy = env_http_proxy.split('://')[-1]
                env_http_proxy = env_http_proxy.split('@')

                if len(env_http_proxy) == 2:
                    login = env_http_proxy[0].split(':')
                    addr = env_http_proxy[1].split(':')
                else:
                    login = ['', '']
                    addr = env_http_proxy[0].split(':')

                proxy = {'host': addr[0], 'type' : 'http', 'user':login[0]}

                if len(addr) == 2:
                    proxy['port'] = addr[1]
                else:
                    proxy['port'] = 3128

                if len(login) == 2:
                    proxy['pass'] = login[1]
                    proxy['useauth'] = True
                else:
                    proxy['pass'] = ''
                return proxy

            except Exception:
                proxy = None
        p = app.config.get('global_proxy')
    if p and p in app.config.get_per('proxies'):
        proxy = {}
        proxyptr = app.config.get_per('proxies', p)
        if not proxyptr:
            return proxy
        for key in proxyptr.keys():
            proxy[key] = proxyptr[key]
        return proxy

def _get_img_direct(attrs):
    """
    Download an image. This function should be launched in a separated thread.
    """
    mem = b''
    alt = ''
    max_size = 2*1024*1024
    if 'max_size' in attrs:
        max_size = attrs['max_size']
    # Wait maximum 10s for connection
    socket.setdefaulttimeout(10)
    try:
        req = urllib.request.Request(attrs['src'])
        req.add_header('User-Agent', 'Gajim ' + app.version)
        f = urllib.request.urlopen(req)
    except Exception as ex:
        log.debug('Error loading image %s ', attrs['src']  + str(ex))
        alt = attrs.get('alt', 'Broken image')
    else:
        # Wait 2s between each byte
        try:
            f.fp._sock.fp._sock.settimeout(2)
        except Exception:
            pass
        # On a slow internet connection with ~1000kbps you need ~10 seconds for 1 MB
        deadline = time.time() + (10 * (max_size / 1048576))
        while True:
            if time.time() > deadline:
                log.debug('Timeout loading image %s ', attrs['src'])
                mem = ''
                alt = attrs.get('alt', '')
                if alt:
                    alt += '\n'
                alt += _('Timeout loading image')
                break
            try:
                temp = f.read(100)
            except socket.timeout as ex:
                log.debug('Timeout loading image %s ', attrs['src'] + str(ex))
                alt = attrs.get('alt', '')
                if alt:
                    alt += '\n'
                alt += _('Timeout loading image')
                break
            if temp:
                mem += temp
            else:
                break
            if len(mem) > max_size:
                alt = attrs.get('alt', '')
                if alt:
                    alt += '\n'
                alt += _('Image is too big')
                break
        f.close()
    return (mem, alt)

def _get_img_proxy(attrs, proxy):
    """
    Download an image through a proxy. This function should be launched in a
    separated thread.
    """
    if not app.is_installed('PYCURL'):
        return '', _('PyCURL is not installed')
    alt, max_size = '', 2*1024*1024
    if 'max_size' in attrs:
        max_size = attrs['max_size']
    try:
        b = StringIO()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, attrs['src'].encode('utf-8'))
        c.setopt(pycurl.FOLLOWLOCATION, 1)
        # Wait maximum 10s for connection
        c.setopt(pycurl.CONNECTTIMEOUT, 10)
        # On a slow internet connection with ~1000kbps you need ~10 seconds for 1 MB
        c.setopt(pycurl.TIMEOUT, 10 * (max_size / 1048576))
        c.setopt(pycurl.MAXFILESIZE, max_size)
        c.setopt(pycurl.WRITEFUNCTION, b.write)
        c.setopt(pycurl.USERAGENT, 'Gajim ' + app.version)
        # set proxy
        c.setopt(pycurl.PROXY, proxy['host'].encode('utf-8'))
        c.setopt(pycurl.PROXYPORT, proxy['port'])
        if proxy['useauth']:
            c.setopt(pycurl.PROXYUSERPWD, proxy['user'].encode('utf-8')\
                + ':' + proxy['pass'].encode('utf-8'))
            c.setopt(pycurl.PROXYAUTH, pycurl.HTTPAUTH_ANY)
        if proxy['type'] == 'http':
            c.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
        elif proxy['type'] == 'socks5':
            c.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        c.close()
        t = b.getvalue()
        return (t, attrs.get('alt', ''))
    except pycurl.error as ex:
        alt = attrs.get('alt', '')
        if alt:
            alt += '\n'
        if ex.errno == pycurl.E_FILESIZE_EXCEEDED:
            alt += _('Image is too big')
        elif ex.errno == pycurl.E_OPERATION_TIMEOUTED:
            alt += _('Timeout loading image')
        else:
            alt += _('Error loading image')
    except Exception as ex:
        log.debug('Error loading image %s ', attrs['src']  + str(ex))
        alt = attrs.get('alt', 'Broken image')
    return ('', alt)

def download_image(account, attrs):
    proxy = get_proxy_info(account)
    if proxy and proxy['type'] in ('http', 'socks5'):
        return _get_img_proxy(attrs, proxy)
    return _get_img_direct(attrs)

def version_condition(current_version, required_version):
    if V(current_version) < V(required_version):
        return False
    return True

def get_available_emoticon_themes():
    emoticons_themes = ['font']
    files = []
    dir_iterator = os.scandir(configpaths.get('EMOTICONS'))
    for folder in dir_iterator:
        if not folder.is_dir():
            continue
        file_iterator = os.scandir(folder.path)
        for theme in file_iterator:
            if theme.is_file():
                files.append(theme.name)

    if os.path.isdir(configpaths.get('MY_EMOTS')):
        files += os.listdir(configpaths.get('MY_EMOTS'))

    for file in files:
        if file.endswith('.png'):
            emoticons_themes.append(file[:-4])
    emoticons_themes.sort()
    return emoticons_themes

def call_counter(func):
    def helper(self, restart=False):
        if restart:
            self._connect_machine_calls = 0
        self._connect_machine_calls += 1
        return func(self, restart=False)
    return helper

def get_sync_threshold(jid, archive_info):
    disco_info = app.logger.get_last_disco_info(jid)
    if archive_info is None or archive_info.sync_threshold is None:
        if disco_info is not None and disco_info.muc_is_members_only:
            threshold = app.config.get('private_room_sync_threshold')
        else:
            threshold = app.config.get('public_room_sync_threshold')
        app.logger.set_archive_infos(jid, sync_threshold=threshold)
        return threshold
    return archive_info.sync_threshold

def load_json(path, key=None, default=None):
    try:
        with open(path, 'r') as file:
            json_dict = json.loads(file.read())
    except Exception:
        log.exception('Parsing error')
        return default

    if key is None:
        return json_dict
    return json_dict.get(key, default)

def ignore_contact(account, jid):
    jid = str(jid)
    known_contact = app.contacts.get_contacts(account, jid)
    ignore = app.config.get_per('accounts', account, 'ignore_unknown_contacts')
    if ignore and not known_contact:
        log.info('Ignore unknown contact %s', jid)
        return True
    return False

class AdditionalDataDict(collections.UserDict):
    def __init__(self, initialdata=None):
        collections.UserDict.__init__(self, initialdata)

    @staticmethod
    def _get_path_childs(full_path):
        path_childs = [full_path]
        if ':' in full_path:
            path_childs = full_path.split(':')
        return path_childs

    def set_value(self, full_path, key, value):
        path_childs = self._get_path_childs(full_path)
        _dict = self.data
        for path in path_childs:
            try:
                _dict = _dict[path]
            except KeyError:
                _dict[path] = {}
                _dict = _dict[path]
        _dict[key] = value

    def get_value(self, full_path, key, default=None):
        path_childs = self._get_path_childs(full_path)
        _dict = self.data
        for path in path_childs:
            try:
                _dict = _dict[path]
            except KeyError:
                return default
        try:
            return _dict[key]
        except KeyError:
            return default

    def remove_value(self, full_path, key):
        path_childs = self._get_path_childs(full_path)
        _dict = self.data
        for path in path_childs:
            try:
                _dict = _dict[path]
            except KeyError:
                return
        try:
            del _dict[key]
        except KeyError:
            return


def save_roster_position(window):
    if not app.config.get('save-roster-position'):
        return
    if app.is_display(Display.WAYLAND):
        return
    x_pos, y_pos = window.get_position()
    log.debug('Save roster position: %s %s', x_pos, y_pos)
    app.config.set('roster_x-position', x_pos)
    app.config.set('roster_y-position', y_pos)


class Singleton(type):
    _instances = {}  # type: Dict[Any, Any]
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls]


def delay_execution(milliseconds):
    # Delay the first call for `milliseconds`
    # ignore all other calls while the delay is active
    def delay_execution_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            def timeout_wrapper():
                func(*args, **kwargs)
                delattr(func_wrapper, 'source_id')

            if hasattr(func_wrapper, 'source_id'):
                return
            func_wrapper.source_id = GLib.timeout_add(
                milliseconds, timeout_wrapper)
        return func_wrapper
    return delay_execution_decorator


def event_filter(filter_):
    def event_filter_decorator(func):
        @wraps(func)
        def func_wrapper(self, event, *args, **kwargs):
            for attr in filter_:
                if '=' in attr:
                    attr1, attr2 = attr.split('=')
                else:
                    attr1, attr2 = attr, attr
                try:
                    if getattr(event, attr1) != getattr(self, attr2):
                        return None
                except AttributeError:
                    if getattr(event, attr1) != getattr(self, '_%s' % attr2):
                        return None

            return func(self, event, *args, **kwargs)
        return func_wrapper
    return event_filter_decorator


def catch_exceptions(func):
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
        except Exception as error:
            log.exception(error)
            return None
        return result
    return func_wrapper


def parse_uri_actions(uri):
    uri = uri[5:]
    if '?' not in uri:
        return 'message', {'jid': uri}

    jid, action = uri.split('?', 1)
    data = {'jid': jid}
    if ';' in action:
        action, keys = action.split(';', 1)
        action_keys = keys.split(';')
        for key in action_keys:
            if key.startswith('subject='):
                data['subject'] = unquote(key[8:])

            elif key.startswith('body='):
                data['body'] = unquote(key[5:])

            elif key.startswith('thread='):
                data['thread'] = key[7:]
    return action, data


def parse_uri(uri):
    if uri.startswith('xmpp:'):
        action, data = parse_uri_actions(uri)
        try:
            validate_jid(data['jid'])
            return URI(type=URIType.XMPP,
                       action=URIAction(action),
                       data=data)
        except ValueError:
            # Unknown action
            return URI(type=URIType.UNKNOWN)

    if uri.startswith('mailto:'):
        uri = uri[7:]
        return URI(type=URIType.MAIL, data=uri)

    if app.interface.sth_at_sth_dot_sth_re.match(uri):
        return URI(type=URIType.AT, data=uri)

    if uri.startswith('geo:'):
        location = uri[4:]
        lat, _, lon = location.partition(',')
        if not lon:
            return URI(type=URIType.UNKNOWN, data=uri)

        uri = geo_provider_from_location(lat, lon)
        return URI(type=URIType.GEO, data=uri)

    if uri.startswith('file://'):
        return URI(type=URIType.FILE, data=uri)

    return URI(type=URIType.WEB, data=uri)


@catch_exceptions
def open_uri(uri, account=None):
    if not isinstance(uri, URI):
        uri = parse_uri(uri)

    if uri.type == URIType.FILE:
        open_file(uri.data)

    elif uri.type == URIType.MAIL:
        uri = 'mailto:%s' % uri.data
        if os.name == 'nt':
            webbrowser.open(uri)
        else:
            Gio.AppInfo.launch_default_for_uri(uri)

    elif uri.type in (URIType.WEB, URIType.GEO):
        if os.name == 'nt':
            webbrowser.open(uri.data)
        else:
            Gio.AppInfo.launch_default_for_uri(uri.data)

    elif uri.type == URIType.AT:
        app.interface.new_chat_from_jid(account, uri.data)

    elif uri.type == URIType.XMPP:
        if account is None:
            log.warning('Account must be specified to open XMPP uri')
            return

        if uri.action == URIAction.JOIN:
            app.app.activate_action(
                'groupchat-join',
                GLib.Variant('as', [account, uri.data['jid']]))
        elif uri.action == URIAction.MESSAGE:
            app.interface.new_chat_from_jid(account, uri.data['jid'],
                                            message=uri.data.get('body'))
        else:
            log.warning('Cant open URI: %s', uri)

    else:
        log.warning('Cant open URI: %s', uri)


@catch_exceptions
def open_file(path):
    if os.name == 'nt':
        os.startfile(path)
    else:
        # Call str() to make it work with pathlib.Path
        path = str(path)
        if not path.startswith('file://'):
            path = 'file://' + path
        Gio.AppInfo.launch_default_for_uri(path)


def geo_provider_from_location(lat, lon):
    return ('https://www.openstreetmap.org/?'
            'mlat=%s&mlon=%s&zoom=16') % (lat, lon)


def get_resource(account):
    resource = app.config.get_per('accounts', account, 'resource')
    # All valid resource substitution strings should be added to this hash.
    if resource:
        rand = ''.join(random.choice(
            string.ascii_uppercase + string.digits) for _ in range(8))
        resource = Template(resource).safe_substitute(
            {'hostname': socket.gethostname(),
             'rand': rand})
        app.config.set_per('accounts', account, 'resource', resource)
    return resource


def get_default_muc_config():
    return {
        # XEP-0045 options
        'muc#roomconfig_allowinvites': True,
        'muc#roomconfig_publicroom': False,
        'muc#roomconfig_membersonly': True,
        'muc#roomconfig_persistentroom': True,
        'muc#roomconfig_whois': 'anyone',
        'muc#roomconfig_moderatedroom': False,

        # Ejabberd options
        'allow_voice_requests': False,
        'public_list': False,

        # Prosody options
        '{http://prosody.im/protocol/muc}roomconfig_allowmemberinvites': True,
        'muc#roomconfig_enablearchiving': True,
    }


def validate_jid(jid, type_=None):
    try:
        jid = JID(str(jid))
    except InvalidJid as error:
        raise ValueError(error)

    if type_ is None:
        return jid
    if type_ == 'bare' and jid.isBare:
        return jid
    if type_ == 'full' and jid.isFull:
        return jid
    if type_ == 'domain' and jid.isDomain:
        return jid

    raise ValueError('Not a %s JID' % type_)


def to_user_string(error):
    text = error.get_text(get_rfc5646_lang())
    if text:
        return text

    condition = error.condition
    if error.app_condition is not None:
        return '%s (%s)' % (condition, error.app_condition)
    return condition


def get_groupchat_name(con, jid):
    name = con.get_module('Bookmarks').get_name_from_bookmark(jid)
    if name:
        return name

    disco_info = app.logger.get_last_disco_info(jid)
    if disco_info is not None:
        if disco_info.muc_name:
            return disco_info.muc_name

    return jid.split('@')[0]


def get_alternative_venue(error):
    if error.condition == 'gone' and error.condition_data is not None:
        uri = parse_uri(error.condition_data)
        if uri.type == URIType.XMPP and uri.action == URIAction.JOIN:
            return uri.data['jid']


def is_affiliation_change_allowed(self_contact, contact, target_aff):
    if contact.affiliation.value == target_aff:
        # Contact has already the target affiliation
        return False

    if self_contact.affiliation.is_owner:
        return True

    if not self_contact.affiliation.is_admin:
        return False

    if target_aff in ('admin', 'owner'):
        # Admin cant edit admin/owner list
        return False
    return self_contact.affiliation > contact.affiliation


def is_role_change_allowed(self_contact, contact):
    if self_contact.role < Role.MODERATOR:
        return False
    return self_contact.affiliation >= contact.affiliation


def get_tls_error_phrase(tls_error):
    phrase = GIO_TLS_ERRORS.get(tls_error)
    if phrase is None:
        return GIO_TLS_ERRORS.get(Gio.TlsCertificateFlags.GENERIC_ERROR)
    return phrase


class Observable:
    def __init__(self, log_=None):
        self._log = log_
        self._callbacks = defaultdict(list)

    def disconnect_signals(self):
        self._callbacks = defaultdict(list)

    def disconnect(self, object_):
        for signal_name, handlers in self._callbacks.items():
            for handler in list(handlers):
                func = handler()
                if func is None or func.__self__ == object_:
                    self._callbacks[signal_name].remove(handler)

    def connect(self, signal_name, func):
        weak_func = weakref.WeakMethod(func)
        self._callbacks[signal_name].append(weak_func)

    def notify(self, signal_name, *args, **kwargs):
        if self._log is not None:
            self._log.info('Signal: %s', signal_name)

        callbacks = self._callbacks.get(signal_name, [])
        for func in list(callbacks):
            if func() is None:
                self._callbacks[signal_name].remove(func)
                continue
            func()(self, signal_name, *args, **kwargs)


def write_file_async(path, data, callback, user_data=None):
    file = Gio.File.new_for_path(str(path))
    file.create_async(Gio.FileCreateFlags.PRIVATE,
                      GLib.PRIORITY_DEFAULT,
                      None,
                      _on_file_created,
                      (callback, data, user_data))

def _on_file_created(file, result, user_data):
    callback, data, user_data = user_data
    try:
        outputstream = file.create_finish(result)
    except GLib.Error as error:
        callback(False, error, user_data)

    # Pass data as user_data to the callback, because
    # write_all_async() takes not reference to the data
    # and python gc collects it before the data are written
    outputstream.write_all_async(data,
                                 GLib.PRIORITY_DEFAULT,
                                 None,
                                 _on_write_finished,
                                 (callback, data, user_data))

def _on_write_finished(outputstream, result, user_data):
    callback, _data, user_data = user_data
    try:
        successful, _bytes_written = outputstream.write_all_finish(result)
    except GLib.Error as error:
        callback(False, error, user_data)
    else:
        callback(successful, None, user_data)


def load_file_async(path, callback, user_data=None):
    file = Gio.File.new_for_path(str(path))
    file.load_contents_async(None,
                             _on_load_finished,
                             (callback, user_data))

def _on_load_finished(file, result, user_data):
    callback, user_data = user_data
    try:
        _successful, contents, _etag = file.load_contents_finish(result)
    except GLib.Error as error:
        callback(None, error, user_data)
    else:
        callback(contents, None, user_data)
