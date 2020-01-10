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
Global Events Dispatcher module.

:author: Mateusz Biliński <mateusz@bilinski.it>
:since: 8th August 2008
:copyright: Copyright (2008) Mateusz Biliński <mateusz@bilinski.it>
:copyright: Copyright (2011) Yann Leboulanger <asterix@lagaule.org>
:license: GPL
'''

import logging
import traceback
import inspect

from nbxmpp import NodeProcessed

log = logging.getLogger('gajim.c.ged')

PRECORE = 10
CORE = 20
POSTCORE = 30
PREGUI = 40
PREGUI1 = 50
GUI1 = 60
POSTGUI1 = 70
PREGUI2 = 80
GUI2 = 90
POSTGUI2 = 100
POSTGUI = 110

OUT_PREGUI = 10
OUT_PREGUI1 = 20
OUT_GUI1 = 30
OUT_POSTGUI1 = 40
OUT_PREGUI2 = 50
OUT_GUI2 = 60
OUT_POSTGUI2 = 70
OUT_POSTGUI = 80
OUT_PRECORE = 90
OUT_CORE = 100
OUT_POSTCORE = 110

class GlobalEventsDispatcher:

    def __init__(self):
        self.handlers = {}

    def register_event_handler(self, event_name, priority, handler):
        if event_name in self.handlers:
            handlers_list = self.handlers[event_name]
            i = 0
            for i, handler_tuple in enumerate(handlers_list):
                if priority < handler_tuple[0]:
                    break
            else:
                # no event with smaller prio found, put it at the end
                i += 1

            handlers_list.insert(i, (priority, handler))
        else:
            self.handlers[event_name] = [(priority, handler)]

    def remove_event_handler(self, event_name, priority, handler):
        if event_name in self.handlers:
            try:
                self.handlers[event_name].remove((priority, handler))
            except ValueError as error:
                log.warning(
                    '''Function (%s) with priority "%s" never
                    registered as handler of event "%s". Couldn\'t remove.
                    Error: %s''', handler, priority, event_name, error)

    def raise_event(self, event_name, *args, **kwargs):
        log.debug('Raise event: %s', event_name)
        if event_name in self.handlers:
            node_processed = False
            # Iterate over a copy of the handlers list, so while iterating
            # the original handlers list can be modified
            for _priority, handler in list(self.handlers[event_name]):
                try:
                    if inspect.ismethod(handler):
                        log.debug('Call handler %s on %s',
                                  handler.__name__,
                                  handler.__self__)
                    else:
                        log.debug('Call handler %s', handler.__name__)
                    if handler(*args, **kwargs):
                        return True
                except NodeProcessed:
                    node_processed = True
                except Exception:
                    log.error('Error while running an event handler: %s',
                              handler)
                    traceback.print_exc()
            if node_processed:
                raise NodeProcessed
