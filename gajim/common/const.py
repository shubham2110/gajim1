from enum import IntEnum, Enum, unique
from collections import namedtuple

from gi.repository import Gio

from gajim.common.i18n import _
from gajim.common.i18n import Q_

EncryptionData = namedtuple('EncryptionData', 'additional_data')
EncryptionData.__new__.__defaults__ = (None,)  # type: ignore


class AvatarSize(IntEnum):
    TAB = 16
    ROSTER = 32
    CHAT = 48
    NOTIFICATION = 48
    TOOLTIP = 125
    VCARD = 200
    PUBLISH = 200


class ArchiveState(IntEnum):
    NEVER = 0
    ALL = 1


@unique
class PathLocation(IntEnum):
    CONFIG = 0
    CACHE = 1
    DATA = 2


@unique
class PathType(IntEnum):
    FILE = 0
    FOLDER = 1
    FOLDER_OPTIONAL = 2


@unique
class KindConstant(IntEnum):
    STATUS = 0
    GCSTATUS = 1
    GC_MSG = 2
    SINGLE_MSG_RECV = 3
    CHAT_MSG_RECV = 4
    SINGLE_MSG_SENT = 5
    CHAT_MSG_SENT = 6
    ERROR = 7

    def __str__(self):
        return str(self.value)


@unique
class ShowConstant(IntEnum):
    ONLINE = 0
    CHAT = 1
    AWAY = 2
    XA = 3
    DND = 4
    OFFLINE = 5


@unique
class TypeConstant(IntEnum):
    AIM = 0
    GG = 1
    HTTP_WS = 2
    ICQ = 3
    MSN = 4
    QQ = 5
    SMS = 6
    SMTP = 7
    TLEN = 8
    YAHOO = 9
    NEWMAIL = 10
    RSS = 11
    WEATHER = 12
    MRIM = 13
    NO_TRANSPORT = 14


@unique
class SubscriptionConstant(IntEnum):
    NONE = 0
    TO = 1
    FROM = 2
    BOTH = 3


@unique
class JIDConstant(IntEnum):
    NORMAL_TYPE = 0
    ROOM_TYPE = 1

@unique
class StyleAttr(Enum):
    COLOR = 'color'
    BACKGROUND = 'background'
    FONT = 'font'

@unique
class CSSPriority(IntEnum):
    APPLICATION = 600
    APPLICATION_DARK = 601
    DEFAULT_THEME = 610
    DEFAULT_THEME_DARK = 611
    USER_THEME = 650

@unique
class ButtonAction(Enum):
    DESTRUCTIVE = 'destructive-action'
    SUGGESTED = 'suggested-action'

@unique
class IdleState(IntEnum):
    UNKNOWN = 0
    XA = 1
    AWAY = 2
    AWAKE = 3


@unique
class RequestAvatar(IntEnum):
    SELF = 0
    ROOM = 1
    USER = 2


@unique
class PEPEventType(IntEnum):
    ABSTRACT = 0
    ACTIVITY = 1
    TUNE = 2
    MOOD = 3
    LOCATION = 4
    NICKNAME = 5
    AVATAR = 6
    ATOM = 7
    BOOKMARKS = 8


@unique
class Chatstate(IntEnum):
    COMPOSING = 0
    PAUSED = 1
    ACTIVE = 2
    INACTIVE = 3
    GONE = 4

    def __str__(self):
        return self.name.lower()


class SyncThreshold(IntEnum):
    NO_THRESHOLD = 0

    def __str__(self):
        return str(self.value)


class MUCUser(IntEnum):
    JID = 0
    NICK = 1
    REASON = 1
    NICK_OR_REASON = 1
    ROLE = 2
    AFFILIATION = 3
    AFFILIATION_TEXT = 4


@unique
class Trust(IntEnum):
    UNTRUSTED = 0
    UNDECIDED = 1
    BLIND = 2
    VERIFIED = 3


class Display(Enum):
    X11 = 'X11Display'
    WAYLAND = 'GdkWaylandDisplay'
    WIN32 = 'GdkWin32Display'
    QUARTZ = 'GdkQuartzDisplay'


class URIType(Enum):
    UNKNOWN = 'unknown'
    XMPP = 'xmpp'
    MAIL = 'mail'
    GEO = 'geo'
    WEB = 'web'
    FILE = 'file'
    AT = 'at'


class URIAction(Enum):
    MESSAGE = 'message'
    JOIN = 'join'
    SUBSCRIBE = 'subscribe'


class MUCJoinedState(Enum):
    JOINED = 'joined'
    NOT_JOINED = 'not joined'
    JOINING = 'joining'
    CREATING = 'creating'
    CAPTCHA_REQUEST = 'captcha in progress'
    CAPTCHA_FAILED = 'captcha failed'

    def __str__(self):
        return self.name


MUC_CREATION_EXAMPLES = [
    (Q_('?Group chat name:Team'),
     Q_('?Group chat description:Project discussion'),
     Q_('?Group chat address:team')),
    (Q_('?Group chat name:Family'),
     Q_('?Group chat description:Spring gathering'),
     Q_('?Group chat address:family')),
    (Q_('?Group chat name:Vacation'),
     Q_('?Group chat description:Trip planning'),
     Q_('?Group chat address:vacation')),
    (Q_('?Group chat name:Repairs'),
     Q_('?Group chat description:Local help group'),
     Q_('?Group chat address:repairs')),
    (Q_('?Group chat name:News'),
     Q_('?Group chat description:Local news and reports'),
     Q_('?Group chat address:news')),
]


MUC_DISCO_ERRORS = {
    'remote-server-not-found': _('Remote server not found'),
    'remote-server-timeout': _('Remote server timeout'),
    'service-unavailable': _('Address does not belong to a group chat server'),
    'subscription-required': _('Address does not belong to a group chat server'),
    'not-muc-service': _('Address does not belong to a group chat server'),
    'already-exists': _('Group chat already exists'),
    'item-not-found': _('Group chat does not exist'),
    'gone': _('Group chat is closed'),
}


EME_MESSAGES = {
    'urn:xmpp:otr:0':
        _('This message was encrypted with OTR '
          'and could not be decrypted.'),
    'jabber:x:encrypted':
        _('This message was encrypted with Legacy '
          'OpenPGP and could not be decrypted. You can install '
          'the PGP plugin to handle those messages.'),
    'urn:xmpp:openpgp:0':
        _('This message was encrypted with '
          'OpenPGP for XMPP and could not be decrypted. You can install '
          'the OpenPGP plugin to handle those messages.'),
    'fallback':
        _('This message was encrypted with %s '
          'and could not be decrypted.')
}


ACTIVITIES = {
    'doing_chores': {
        'category': _('Doing Chores'),
        'buying_groceries': _('Buying Groceries'),
        'cleaning': _('Cleaning'),
        'cooking': _('Cooking'),
        'doing_maintenance': _('Doing Maintenance'),
        'doing_the_dishes': _('Doing the Dishes'),
        'doing_the_laundry': _('Doing the Laundry'),
        'gardening': _('Gardening'),
        'running_an_errand': _('Running an Errand'),
        'walking_the_dog': _('Walking the Dog')},
    'drinking': {
        'category': _('Drinking'),
        'having_a_beer': _('Having a Beer'),
        'having_coffee': _('Having Coffee'),
        'having_tea': _('Having Tea')},
    'eating': {
        'category': _('Eating'),
        'having_a_snack': _('Having a Snack'),
        'having_breakfast': _('Having Breakfast'),
        'having_dinner': _('Having Dinner'),
        'having_lunch': _('Having Lunch')},
    'exercising': {
        'category': _('Exercising'),
        'cycling': _('Cycling'),
        'dancing': _('Dancing'),
        'hiking': _('Hiking'),
        'jogging': _('Jogging'),
        'playing_sports': _('Playing Sports'),
        'running': _('Running'),
        'skiing': _('Skiing'),
        'swimming': _('Swimming'),
        'working_out': _('Working out')},
    'grooming': {
        'category': _('Grooming'),
        'at_the_spa': _('At the Spa'),
        'brushing_teeth': _('Brushing Teeth'),
        'getting_a_haircut': _('Getting a Haircut'),
        'shaving': _('Shaving'),
        'taking_a_bath': _('Taking a Bath'),
        'taking_a_shower': _('Taking a Shower')},
    'having_appointment': {
        'category': _('Having an Appointment')},
    'inactive': {
        'category': _('Inactive'),
        'day_off': _('Day Off'),
        'hanging_out': _('Hanging out'),
        'hiding': _('Hiding'),
        'on_vacation': _('On Vacation'),
        'praying': _('Praying'),
        'scheduled_holiday': _('Scheduled Holiday'),
        'sleeping': _('Sleeping'),
        'thinking': _('Thinking')},
    'relaxing': {
        'category': _('Relaxing'),
        'fishing': _('Fishing'),
        'gaming': _('Gaming'),
        'going_out': _('Going out'),
        'partying': _('Partying'),
        'reading': _('Reading'),
        'rehearsing': _('Rehearsing'),
        'shopping': _('Shopping'),
        'smoking': _('Smoking'),
        'socializing': _('Socializing'),
        'sunbathing': _('Sunbathing'),
        'watching_tv': _('Watching TV'),
        'watching_a_movie': _('Watching a Movie')},
    'talking': {
        'category': _('Talking'),
        'in_real_life': _('In Real Life'),
        'on_the_phone': _('On the Phone'),
        'on_video_phone': _('On Video Phone')},
    'traveling': {
        'category': _('Traveling'),
        'commuting': _('Commuting'),
        'cycling': _('Cycling'),
        'driving': _('Driving'),
        'in_a_car': _('In a Car'),
        'on_a_bus': _('On a Bus'),
        'on_a_plane': _('On a Plane'),
        'on_a_train': _('On a Train'),
        'on_a_trip': _('On a Trip'),
        'walking': _('Walking')},
    'working': {
        'category': _('Working'),
        'coding': _('Coding'),
        'in_a_meeting': _('In a Meeting'),
        'studying': _('Studying'),
        'writing': _('Writing')}}

MOODS = {
    'afraid': _('Afraid'),
    'amazed': _('Amazed'),
    'amorous': _('Amorous'),
    'angry': _('Angry'),
    'annoyed': _('Annoyed'),
    'anxious': _('Anxious'),
    'aroused': _('Aroused'),
    'ashamed': _('Ashamed'),
    'bored': _('Bored'),
    'brave': _('Brave'),
    'calm': _('Calm'),
    'cautious': _('Cautious'),
    'cold': _('Cold'),
    'confident': _('Confident'),
    'confused': _('Confused'),
    'contemplative': _('Contemplative'),
    'contented': _('Contented'),
    'cranky': _('Cranky'),
    'crazy': _('Crazy'),
    'creative': _('Creative'),
    'curious': _('Curious'),
    'dejected': _('Dejected'),
    'depressed': _('Depressed'),
    'disappointed': _('Disappointed'),
    'disgusted': _('Disgusted'),
    'dismayed': _('Dismayed'),
    'distracted': _('Distracted'),
    'embarrassed': _('Embarrassed'),
    'envious': _('Envious'),
    'excited': _('Excited'),
    'flirtatious': _('Flirtatious'),
    'frustrated': _('Frustrated'),
    'grateful': _('Grateful'),
    'grieving': _('Grieving'),
    'grumpy': _('Grumpy'),
    'guilty': _('Guilty'),
    'happy': _('Happy'),
    'hopeful': _('Hopeful'),
    'hot': _('Hot'),
    'humbled': _('Humbled'),
    'humiliated': _('Humiliated'),
    'hungry': _('Hungry'),
    'hurt': _('Hurt'),
    'impressed': _('Impressed'),
    'in_awe': _('In Awe'),
    'in_love': _('In Love'),
    'indignant': _('Indignant'),
    'interested': _('Interested'),
    'intoxicated': _('Intoxicated'),
    'invincible': _('Invincible'),
    'jealous': _('Jealous'),
    'lonely': _('Lonely'),
    'lost': _('Lost'),
    'lucky': _('Lucky'),
    'mean': _('Mean'),
    'moody': _('Moody'),
    'nervous': _('Nervous'),
    'neutral': _('Neutral'),
    'offended': _('Offended'),
    'outraged': _('Outraged'),
    'playful': _('Playful'),
    'proud': _('Proud'),
    'relaxed': _('Relaxed'),
    'relieved': _('Relieved'),
    'remorseful': _('Remorseful'),
    'restless': _('Restless'),
    'sad': _('Sad'),
    'sarcastic': _('Sarcastic'),
    'satisfied': _('Satisfied'),
    'serious': _('Serious'),
    'shocked': _('Shocked'),
    'shy': _('Shy'),
    'sick': _('Sick'),
    'sleepy': _('Sleepy'),
    'spontaneous': _('Spontaneous'),
    'stressed': _('Stressed'),
    'strong': _('Strong'),
    'surprised': _('Surprised'),
    'thankful': _('Thankful'),
    'thirsty': _('Thirsty'),
    'tired': _('Tired'),
    'undefined': _('Undefined'),
    'weak': _('Weak'),
    'worried': _('Worried')
}

LOCATION_DATA = {
    'accuracy': _('accuracy'),
    'alt': _('alt'),
    'area': _('area'),
    'bearing': _('bearing'),
    'building': _('building'),
    'country': _('country'),
    'countrycode': _('countrycode'),
    'datum': _('datum'),
    'description': _('description'),
    'error': _('error'),
    'floor': _('floor'),
    'lat': _('lat'),
    'locality': _('locality'),
    'lon': _('lon'),
    'postalcode': _('postalcode'),
    'region': _('region'),
    'room': _('room'),
    'speed': _('speed'),
    'street': _('street'),
    'text': _('text'),
    'timestamp': _('timestamp'),
    'uri': _('URI')
}


SSLError = {
    2: _("Unable to get issuer certificate"),
    3: _("Unable to get certificate CRL"),
    4: _("Unable to decrypt certificate's signature"),
    5: _("Unable to decrypt CRL's signature"),
    6: _("Unable to decode issuer public key"),
    7: _("Certificate signature failure"),
    8: _("CRL signature failure"),
    9: _("Certificate is not yet valid"),
    10: _("Certificate has expired"),
    11: _("CRL is not yet valid"),
    12: _("CRL has expired"),
    13: _("Format error in certificate's notBefore field"),
    14: _("Format error in certificate's notAfter field"),
    15: _("Format error in CRL's lastUpdate field"),
    16: _("Format error in CRL's nextUpdate field"),
    17: _("Out of memory"),
    18: _("Self signed certificate"),
    19: _("Self signed certificate in certificate chain"),
    20: _("Unable to get local issuer certificate"),
    21: _("Unable to verify the first certificate"),
    22: _("Certificate chain too long"),
    23: _("Certificate revoked"),
    24: _("Invalid CA certificate"),
    25: _("Path length constraint exceeded"),
    26: _("Unsupported certificate purpose"),
    27: _("Certificate not trusted"),
    28: _("Certificate rejected"),
    29: _("Subject issuer mismatch"),
    30: _("Authority and subject key identifier mismatch"),
    31: _("Authority and issuer serial number mismatch"),
    32: _("Key usage does not include certificate signing"),
    50: _("Application verification failure"),
}


THANKS = u"""\
Alexander Futász
Alexander V. Butenko
Alexey Nezhdanov
Alfredo Junix
Anaël Verrier
Anders Ström
Andrew Sayman
Anton Shmigirilov
Christian Bjälevik
Christophe Got
Christoph Neuroth
David Campey
Dennis Craven
Fabian Neumann
Filippos Papadopoulos
Francisco Alburquerque Parra (Membris Khan)
Frederic Lory
Fridtjof Bussefor
Geobert Quach
Guillaume Morin
Gustavo J. A. M. Carneiro
Ivo Anjo
Josef Vybíral
Juraj Michalek
Kjell Braden
Luis Peralta
Michael Scherer
Michele Campeotto
Mike Albon
Miguel Fonseca
Norman Rasmussen
Oscar Hellström
Peter Saint-Andre
Petr Menšík
Sergey Kuleshov
Stavros Giannouris
Stian B. Barmen
Thilo Molitor
Thomas Klein-Hitpaß
Urtzi Alfaro
Witold Kieraś
Yakov Bezrukov
Yavor Doganov
""".strip().split("\n")

ARTISTS = u"""\
Anders Ström
Christophe Got
Dennis Craven
Dmitry Korzhevin
Guillaume Morin
Gvorcek Spajreh
Josef Vybíral
Membris Khan
Rederick Asher
Jakub Szypulka
""".strip().split("\n")

DEVS_CURRENT = u"""\
Yann Leboulanger (asterix AT lagaule.org)
Philipp Hörist (philipp AT hoerist.com)
""".strip().split("\n")

DEVS_PAST = u"""\
Stefan Bethge (stefan AT lanpartei.de)
Alexander Cherniuk (ts33kr AT gmail.com)
Stephan Erb (steve-e AT h3c.de)
Vincent Hanquez (tab AT snarc.org)
Dimitur Kirov (dkirov AT gmail.com)
Nikos Kouremenos (kourem AT gmail.com)
Julien Pivotto (roidelapluie AT gmail.com)
Jonathan Schleifer (js-gajim AT webkeks.org)
Travis Shirk (travis AT pobox.com)
Brendan Taylor (whateley AT gmail.com)
Jean-Marie Traissard (jim AT lapin.org)
""".strip().split("\n")


RFC5646_LANGUAGE_TAGS = {
    'af': 'Afrikaans',
    'af-ZA': 'Afrikaans (South Africa)',
    'ar': 'Arabic',
    'ar-AE': 'Arabic (U.A.E.)',
    'ar-BH': 'Arabic (Bahrain)',
    'ar-DZ': 'Arabic (Algeria)',
    'ar-EG': 'Arabic (Egypt)',
    'ar-IQ': 'Arabic (Iraq)',
    'ar-JO': 'Arabic (Jordan)',
    'ar-KW': 'Arabic (Kuwait)',
    'ar-LB': 'Arabic (Lebanon)',
    'ar-LY': 'Arabic (Libya)',
    'ar-MA': 'Arabic (Morocco)',
    'ar-OM': 'Arabic (Oman)',
    'ar-QA': 'Arabic (Qatar)',
    'ar-SA': 'Arabic (Saudi Arabia)',
    'ar-SY': 'Arabic (Syria)',
    'ar-TN': 'Arabic (Tunisia)',
    'ar-YE': 'Arabic (Yemen)',
    'az': 'Azeri (Latin)',
    'az-AZ': 'Azeri (Latin) (Azerbaijan)',
    'az-Cyrl-AZ': 'Azeri (Cyrillic) (Azerbaijan)',
    'be': 'Belarusian',
    'be-BY': 'Belarusian (Belarus)',
    'bg': 'Bulgarian',
    'bg-BG': 'Bulgarian (Bulgaria)',
    'bs-BA': 'Bosnian (Bosnia and Herzegovina)',
    'ca': 'Catalan',
    'ca-ES': 'Catalan (Spain)',
    'cs': 'Czech',
    'cs-CZ': 'Czech (Czech Republic)',
    'cy': 'Welsh',
    'cy-GB': 'Welsh (United Kingdom)',
    'da': 'Danish',
    'da-DK': 'Danish (Denmark)',
    'de': 'German',
    'de-AT': 'German (Austria)',
    'de-CH': 'German (Switzerland)',
    'de-DE': 'German (Germany)',
    'de-LI': 'German (Liechtenstein)',
    'de-LU': 'German (Luxembourg)',
    'dv': 'Divehi',
    'dv-MV': 'Divehi (Maldives)',
    'el': 'Greek',
    'el-GR': 'Greek (Greece)',
    'en': 'English',
    'en-AU': 'English (Australia)',
    'en-BZ': 'English (Belize)',
    'en-CA': 'English (Canada)',
    'en-CB': 'English (Caribbean)',
    'en-GB': 'English (United Kingdom)',
    'en-IE': 'English (Ireland)',
    'en-JM': 'English (Jamaica)',
    'en-NZ': 'English (New Zealand)',
    'en-PH': 'English (Republic of the Philippines)',
    'en-TT': 'English (Trinidad and Tobago)',
    'en-US': 'English (United States)',
    'en-ZA': 'English (South Africa)',
    'en-ZW': 'English (Zimbabwe)',
    'eo': 'Esperanto',
    'es': 'Spanish',
    'es-AR': 'Spanish (Argentina)',
    'es-BO': 'Spanish (Bolivia)',
    'es-CL': 'Spanish (Chile)',
    'es-CO': 'Spanish (Colombia)',
    'es-CR': 'Spanish (Costa Rica)',
    'es-DO': 'Spanish (Dominican Republic)',
    'es-EC': 'Spanish (Ecuador)',
    'es-ES': 'Spanish (Spain)',
    'es-GT': 'Spanish (Guatemala)',
    'es-HN': 'Spanish (Honduras)',
    'es-MX': 'Spanish (Mexico)',
    'es-NI': 'Spanish (Nicaragua)',
    'es-PA': 'Spanish (Panama)',
    'es-PE': 'Spanish (Peru)',
    'es-PR': 'Spanish (Puerto Rico)',
    'es-PY': 'Spanish (Paraguay)',
    'es-SV': 'Spanish (El Salvador)',
    'es-UY': 'Spanish (Uruguay)',
    'es-VE': 'Spanish (Venezuela)',
    'et': 'Estonian',
    'et-EE': 'Estonian (Estonia)',
    'eu': 'Basque',
    'eu-ES': 'Basque (Spain)',
    'fa': 'Farsi',
    'fa-IR': 'Farsi (Iran)',
    'fi': 'Finnish',
    'fi-FI': 'Finnish (Finland)',
    'fo': 'Faroese',
    'fo-FO': 'Faroese (Faroe Islands)',
    'fr': 'French',
    'fr-BE': 'French (Belgium)',
    'fr-CA': 'French (Canada)',
    'fr-CH': 'French (Switzerland)',
    'fr-FR': 'French (France)',
    'fr-LU': 'French (Luxembourg)',
    'fr-MC': 'French (Principality of Monaco)',
    'gl': 'Galician',
    'gl-ES': 'Galician (Spain)',
    'gu': 'Gujarati',
    'gu-IN': 'Gujarati (India)',
    'he': 'Hebrew',
    'he-IL': 'Hebrew (Israel)',
    'hi': 'Hindi',
    'hi-IN': 'Hindi (India)',
    'hr': 'Croatian',
    'hr-BA': 'Croatian (Bosnia and Herzegovina)',
    'hr-HR': 'Croatian (Croatia)',
    'hu': 'Hungarian',
    'hu-HU': 'Hungarian (Hungary)',
    'hy': 'Armenian',
    'hy-AM': 'Armenian (Armenia)',
    'id': 'Indonesian',
    'id-ID': 'Indonesian (Indonesia)',
    'is': 'Icelandic',
    'is-IS': 'Icelandic (Iceland)',
    'it': 'Italian',
    'it-CH': 'Italian (Switzerland)',
    'it-IT': 'Italian (Italy)',
    'ja': 'Japanese',
    'ja-JP': 'Japanese (Japan)',
    'ka': 'Georgian',
    'ka-GE': 'Georgian (Georgia)',
    'kk': 'Kazakh',
    'kk-KZ': 'Kazakh (Kazakhstan)',
    'kn': 'Kannada',
    'kn-IN': 'Kannada (India)',
    'ko': 'Korean',
    'ko-KR': 'Korean (Korea)',
    'kok': 'Konkani',
    'kok-IN': 'Konkani (India)',
    'ky': 'Kyrgyz',
    'ky-KG': 'Kyrgyz (Kyrgyzstan)',
    'lt': 'Lithuanian',
    'lt-LT': 'Lithuanian (Lithuania)',
    'lv': 'Latvian',
    'lv-LV': 'Latvian (Latvia)',
    'mi': 'Maori',
    'mi-NZ': 'Maori (New Zealand)',
    'mk': 'FYRO Macedonian',
    'mk-MK': 'FYRO Macedonian (Former Yugoslav Republic of Macedonia)',
    'mn': 'Mongolian',
    'mn-MN': 'Mongolian (Mongolia)',
    'mr': 'Marathi',
    'mr-IN': 'Marathi (India)',
    'ms': 'Malay',
    'ms-BN': 'Malay (Brunei Darussalam)',
    'ms-MY': 'Malay (Malaysia)',
    'mt': 'Maltese',
    'mt-MT': 'Maltese (Malta)',
    'nb': 'Norwegian (Bokm?l)',
    'nb-NO': 'Norwegian (Bokm?l) (Norway)',
    'nl': 'Dutch',
    'nl-BE': 'Dutch (Belgium)',
    'nl-NL': 'Dutch (Netherlands)',
    'nn-NO': 'Norwegian (Nynorsk) (Norway)',
    'ns': 'Northern Sotho',
    'ns-ZA': 'Northern Sotho (South Africa)',
    'pa': 'Punjabi',
    'pa-IN': 'Punjabi (India)',
    'pl': 'Polish',
    'pl-PL': 'Polish (Poland)',
    'ps': 'Pashto',
    'ps-AR': 'Pashto (Afghanistan)',
    'pt': 'Portuguese',
    'pt-BR': 'Portuguese (Brazil)',
    'pt-PT': 'Portuguese (Portugal)',
    'qu': 'Quechua',
    'qu-BO': 'Quechua (Bolivia)',
    'qu-EC': 'Quechua (Ecuador)',
    'qu-PE': 'Quechua (Peru)',
    'ro': 'Romanian',
    'ro-RO': 'Romanian (Romania)',
    'ru': 'Russian',
    'ru-RU': 'Russian (Russia)',
    'sa': 'Sanskrit',
    'sa-IN': 'Sanskrit (India)',
    'se': 'Sami',
    'se-FI': 'Sami (Finland)',
    'se-NO': 'Sami (Norway)',
    'se-SE': 'Sami (Sweden)',
    'sk': 'Slovak',
    'sk-SK': 'Slovak (Slovakia)',
    'sl': 'Slovenian',
    'sl-SI': 'Slovenian (Slovenia)',
    'sq': 'Albanian',
    'sq-AL': 'Albanian (Albania)',
    'sr-BA': 'Serbian (Latin) (Bosnia and Herzegovina)',
    'sr-Cyrl-BA': 'Serbian (Cyrillic) (Bosnia and Herzegovina)',
    'sr-SP': 'Serbian (Latin) (Serbia and Montenegro)',
    'sr-Cyrl-SP': 'Serbian (Cyrillic) (Serbia and Montenegro)',
    'sv': 'Swedish',
    'sv-FI': 'Swedish (Finland)',
    'sv-SE': 'Swedish (Sweden)',
    'sw': 'Swahili',
    'sw-KE': 'Swahili (Kenya)',
    'syr': 'Syriac',
    'syr-SY': 'Syriac (Syria)',
    'ta': 'Tamil',
    'ta-IN': 'Tamil (India)',
    'te': 'Telugu',
    'te-IN': 'Telugu (India)',
    'th': 'Thai',
    'th-TH': 'Thai (Thailand)',
    'tl': 'Tagalog',
    'tl-PH': 'Tagalog (Philippines)',
    'tn': 'Tswana',
    'tn-ZA': 'Tswana (South Africa)',
    'tr': 'Turkish',
    'tr-TR': 'Turkish (Turkey)',
    'tt': 'Tatar',
    'tt-RU': 'Tatar (Russia)',
    'ts': 'Tsonga',
    'uk': 'Ukrainian',
    'uk-UA': 'Ukrainian (Ukraine)',
    'ur': 'Urdu',
    'ur-PK': 'Urdu (Islamic Republic of Pakistan)',
    'uz': 'Uzbek (Latin)',
    'uz-UZ': 'Uzbek (Latin) (Uzbekistan)',
    'uz-Cyrl-UZ': 'Uzbek (Cyrillic) (Uzbekistan)',
    'vi': 'Vietnamese',
    'vi-VN': 'Vietnamese (Viet Nam)',
    'xh': 'Xhosa',
    'xh-ZA': 'Xhosa (South Africa)',
    'zh': 'Chinese',
    'zh-CN': 'Chinese (S)',
    'zh-HK': 'Chinese (Hong Kong)',
    'zh-MO': 'Chinese (Macau)',
    'zh-SG': 'Chinese (Singapore)',
    'zh-TW': 'Chinese (T)',
    'zu': 'Zulu',
    'zu-ZA': 'Zulu (South Africa)'
}

# pylint: disable=line-too-long
GIO_TLS_ERRORS = {
    Gio.TlsCertificateFlags.UNKNOWN_CA: _('The signing certificate authority is not known'),
    Gio.TlsCertificateFlags.REVOKED: _('The certificate has been revoked'),
    Gio.TlsCertificateFlags.BAD_IDENTITY: _('The certificate does not match the expected identity of the site'),
    Gio.TlsCertificateFlags.INSECURE: _('The certificate’s algorithm is insecure'),
    Gio.TlsCertificateFlags.NOT_ACTIVATED: _('The certificate’s activation time is in the future'),
    Gio.TlsCertificateFlags.GENERIC_ERROR: _('Unknown validation error'),
    Gio.TlsCertificateFlags.EXPIRED: _('The certificate has expired'),
}
# pylint: enable=line-too-long


class FTState(Enum):
    PREPARING = 'prepare'
    ENCRYPTING = 'encrypting'
    DECRYPTING = 'decrypting'
    STARTED = 'started'
    IN_PROGRESS = 'progress'
    FINISHED = 'finished'
    ERROR = 'error'

    @property
    def is_preparing(self):
        return self == FTState.PREPARING

    @property
    def is_encrypting(self):
        return self == FTState.ENCRYPTING

    @property
    def is_decrypting(self):
        return self == FTState.DECRYPTING

    @property
    def is_started(self):
        return self == FTState.STARTED

    @property
    def is_in_progress(self):
        return self == FTState.IN_PROGRESS

    @property
    def is_finished(self):
        return self == FTState.FINISHED

    @property
    def is_error(self):
        return self == FTState.ERROR
