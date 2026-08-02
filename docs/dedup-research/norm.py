"""Нормализация названий: общая для всех проб."""
import re, unicodedata

ROMAN = {'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7,'viii':8,'ix':9,'x':10,
         'xi':11,'xii':12,'xiii':13}
EDITION_WORDS = {
 'edition','editions','ed','goty','game','of','the','year','deluxe','definitive',
 'enhanced','complete','ultimate','gold','premium','anthology','collection',
 'remastered','remaster','redux','hd','director','directors','cut','special',
 'extended','anniversary','classic','classics','platinum','legendary','bundle',
 'pack','trilogy','collector','collectors','digital','plus','edycja','full',
 'standard','vr','edt','revised','final','master','collected','republic','2in1'}
SYMBOLS = str.maketrans({'™':' ','®':' ','©':' ','℠':' ','’':"'",'‘':"'",
                         '–':'-','—':'-','…':' ','²':'2','³':'3'})

def base(s: str) -> str:
    """Строка → плоское сравнимое написание (без снятия изданий).

    Знаки ® и ™ снимаются ДО NFKC: нормализация разворачивает «™» в буквы «TM»
    и приклеивает их к слову."""
    if not s: return ''
    s = s.replace('> ', ' ').translate(SYMBOLS)
    s = unicodedata.normalize('NFKC', s).translate(SYMBOLS)
    s = s.lower()
    s = re.sub(r'\band\b', ' & ', s)
    s = s.replace('&', ' and ')
    s = re.sub(r"[^0-9a-zа-яё]+", ' ', s)
    parts = [str(ROMAN[p]) if p in ROMAN else p for p in s.split()]
    parts = [p for p in parts if p not in ('the','a','an')]
    return ' '.join(parts)

def strip_edition(s: str) -> str:
    """Снять хвост из издательских слов."""
    parts = base(s).split()
    while parts and parts[-1] in EDITION_WORDS:
        parts.pop()
    return ' '.join(parts) or base(s)

def toks(s: str) -> set:
    return set(strip_edition(s).split())
