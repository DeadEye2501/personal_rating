"""Прогон правил склейки по размеченным парам. Печатает числа, ничего не решает."""
import difflib
import sys

sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from norm import base, strip_edition, toks
from truth import build

INFO, LABELS, _ = build()


def score(name, rule):
    tp = fp = fn = 0
    misses, wrong = [], []
    for key, (a, b, q) in INFO.items():
        got = rule(a, b)
        want = LABELS[key] == 'yes'
        if got and want:
            tp += 1
        elif got and not want:
            fp += 1
            wrong.append((a, b, q))
        elif want:
            fn += 1
            misses.append((a, b, q))
    print(f'{name:52} нашло {tp:3}  ложных {fp:3}  пропустило {fn:3}')
    return tp, fp, fn, wrong, misses


def show(rows, title, limit=99):
    if not rows:
        return
    print(f'    {title}:')
    for a, b, q in rows[:limit]:
        print(f'      [{a[0]}] {a[2]}  ||  [{b[0]}] {b[2]}')


def r_exact(a, b):
    return base(a[2]) == base(b[2])


def r_edition(a, b):
    return strip_edition(a[2]) == strip_edition(b[2])


def years_ok(a, b, slack=1):
    if a[3] is None or b[3] is None:
        return True
    return abs(a[3] - b[3]) <= slack


def r_edition_year(a, b):
    return r_edition(a, b) and years_ok(a, b)


def r_contains(a, b):
    x, y = strip_edition(a[2]).split(), strip_edition(b[2]).split()
    if not x or not y:
        return False
    if len(x) > len(y):
        x, y = y, x
    return y[:len(x)] == x


def r_jaccard(a, b, t=0.6):
    x, y = toks(a[2]), toks(b[2])
    return len(x & y) / max(1, len(x | y)) >= t


def r_ratio(a, b, t=0.85):
    return difflib.SequenceMatcher(None, strip_edition(a[2]),
                                   strip_edition(b[2])).ratio() >= t


def numbers(s):
    return tuple(t for t in strip_edition(s).split() if t.isdigit())


def r_ratio_num(a, b, t=0.85):
    return numbers(a[2]) == numbers(b[2]) and r_ratio(a, b, t)


def r_jaccard_num(a, b, t=0.6):
    return numbers(a[2]) == numbers(b[2]) and r_jaccard(a, b, t)


def slug_key(row):
    if row[0] == 'G':
        return base((row[4].get('slug') or '').replace('_', ' '))
    return base(row[2])


def r_slug(a, b):
    return slug_key(a) == slug_key(b)


def alt_titles(row):
    if row[0] != 'O':
        return [row[2]]
    return [row[2]] + ([row[4]['alt']] if row[4].get('alt') else [])


def r_edition_alt(a, b):
    return any(strip_edition(x) == strip_edition(y)
               for x in alt_titles(a) for y in alt_titles(b))


def people(row):
    got = set()
    for field in ('developers', 'publishers'):
        for one in row[4].get(field) or []:
            got.add(base(one).replace(' llc', '').replace(' inc', '').strip())
    if row[0] == 'O' and row[4].get('publisher'):
        got.add(base(row[4]['publisher']))
    return {x for x in got if x}


def r_people(a, b):
    x, y = people(a), people(b)
    return bool(x and y and x & y)


def r_edition_people(a, b):
    return r_edition(a, b) and (not people(a) or not people(b) or r_people(a, b))


print('=== пар', len(INFO), ', из них одна игра', sum(1 for v in LABELS.values() if v == 'yes'), '===\n')
print('--- одиночные ключи ---')
score('название точно (символы, римские, артикли)', r_exact)
score('название + снятие слов издания', r_edition)
score('то же + год, если известен обоим (±1)', r_edition_year)
score('слаг GOG против названия', r_slug)
score('совпал разработчик или издатель', r_people)
print()
print('--- нечёткие ---')
score('вложение (одно название — начало другого)', r_contains)
score('Жаккар по словам >= 0.6', r_jaccard)
score('Левенштейн (difflib) >= 0.85', r_ratio)
score('Левенштейн >= 0.85 И числа совпали', r_ratio_num)
score('Жаккар >= 0.6 И числа совпали', r_jaccard_num)
print()
print('--- надстройки над рекомендуемым ---')
score('издание + альтернативное название old-games', r_edition_alt)
score('издание + сверка людей, когда известны', r_edition_people)

print('\n=== разбор рекомендуемого правила (название + снятие издания) ===')
tp, fp, fn, wrong, misses = score('оно же', r_edition)
show(wrong, 'ЛОЖНЫЕ СКЛЕЙКИ')
print(f'    ПРОПУЩЕНО {len(misses)}')
show(misses, 'пропущенные верные пары')
