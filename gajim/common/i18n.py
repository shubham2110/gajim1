# Copyright (C) 2003-2014 Yann Leboulanger <asterix AT lagaule.org>
# Copyright (C) 2004 Vincent Hanquez <tab AT snarc.org>
# Copyright (C) 2005-2006 Nikos Kouremenos <kourem AT gmail.com>
# Copyright (C) 2009 Benjamin Richter <br AT waldteufel-online.net>
# Copyright (C) 2018 Philipp Hörist <philipp AT hoerist.com>
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
import sys
import locale
import gettext
import unicodedata
from pathlib import Path

DOMAIN = 'gajim'
LANG = 'en'
direction_mark = '\u200E'
_translation = gettext.NullTranslations()


def get_locale_dirs():
    if os.name == 'nt':
        return

    path = gettext.find(DOMAIN)
    if path is not None:
        # gettext can find the location itself
        # so we dont need the localedir
        return

    if Path('/app/share/run-as-flatpak').exists():
        # Check if we run as flatpak
        return [Path('/app/share/')]

    data_dirs = os.getenv('XDG_DATA_DIRS')
    if data_dirs:
        return list(map(Path, data_dirs.split(':')))
    return [Path('/usr/local/share/'), Path('/usr/share/')]


def iter_locale_dirs():
    locale_dirs = get_locale_dirs()
    if locale_dirs is None:
        yield None
        return

    # gettext fallback
    locale_dirs.append(Path(sys.base_prefix) / 'share')

    found_paths = []
    for path in locale_dirs:
        locale_dir = path / 'locale'
        if locale_dir in found_paths:
            continue
        found_paths.append(locale_dir)
        if locale_dir.is_dir():
            yield str(locale_dir)


def get_default_lang():
    if os.name == "nt":
        import ctypes
        windll = ctypes.windll.kernel32
        return locale.windows_locale[windll.GetUserDefaultUILanguage()]

    if sys.platform == "darwin":
        from AppKit import NSLocale
        # FIXME: This returns a two letter language code (en, de, fr)
        # We need a way to get en_US, de_DE etc.
        return NSLocale.currentLocale().languageCode()

    return locale.getdefaultlocale()[0] or 'en'


def get_rfc5646_lang(lang=None):
    if lang is None:
        lang = LANG
    return lang.replace('_', '-')


def get_short_lang_code(lang=None):
    if lang is None:
        lang = LANG
    return lang[:2]


def initialize_direction_mark():
    from gi.repository import Gtk

    global direction_mark

    if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
        direction_mark = '\u200F'


def paragraph_direction_mark(text):
    """
    Determine paragraph writing direction according to
    http://www.unicode.org/reports/tr9/#The_Paragraph_Level

    Returns either Unicode LTR mark or RTL mark.
    """
    for char in text:
        bidi = unicodedata.bidirectional(char)
        if bidi == 'L':
            return '\u200E'
        if bidi in ('AL', 'R'):
            return '\u200F'

    return '\u200E'


def Q_(text):
    """
    Translate the given text, optionally qualified with a special
    construction, which will help translators to disambiguate between
    same terms, but in different contexts.

    When translated text is returned - this rudimentary construction
    will be stripped off, if it's present.

    Here is the construction to use:
        Q_("?vcard:Unknown")

    Everything between ? and : - is the qualifier to convey the context
    to the translators. Everything after : - is the text itself.
    """
    text = _(text)
    if text.startswith('?'):
        text = text.split(':', 1)[1]
    return text


def ngettext(s_sing, s_plural, n, replace_sing=None, replace_plural=None):
    """
    Use as:
        i18n.ngettext(
            'leave room %s', 'leave rooms %s', len(rooms), 'a', 'a, b, c')

    In other words this is a hack to ngettext() to support %s %d etc..
    """
    text = _translation.ngettext(s_sing, s_plural, n)
    if n == 1 and replace_sing is not None:
        text = text % replace_sing
    elif n > 1 and replace_plural is not None:
        text = text % replace_plural
    return text


try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error as error:
    print(error, file=sys.stderr)

try:
    LANG = get_default_lang()
    if os.name == 'nt':
        # Set the env var on Windows because gettext.find() uses it to
        # find the translation
        # Use LANGUAGE instead of LANG, LANG sets LC_ALL and thus
        # doesn't retain other region settings like LC_TIME
        os.environ['LANGUAGE'] = LANG
except Exception as error:
    print('Failed to determine default language', file=sys.stderr)
    import traceback
    traceback.print_exc()

# Search for the translation in all locale dirs
for dir_ in iter_locale_dirs():
    try:
        _translation = gettext.translation(DOMAIN, dir_)
        _ = _translation.gettext
        if hasattr(locale, 'bindtextdomain'):
            locale.bindtextdomain(DOMAIN, dir_)  # type: ignore
    except OSError:
        continue
    else:
        break
else:
    print('No translations found', file=sys.stderr)
    print('Dirs searched: %s' % get_locale_dirs(), file=sys.stderr)
    _ = _translation.gettext
