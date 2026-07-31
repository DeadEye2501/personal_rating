# План 6. Каркас страницы

> **Исполнителю:** ОБЯЗАТЕЛЬНЫЙ СУБ-СКИЛЛ — `superpowers:subagent-driven-development`
> или `superpowers:executing-plans`. Шаги помечены чекбоксами (`- [ ]`) для отметки
> хода работ.

**Цель:** окно перестаёт показывать заглушку. Появляется настоящая страница:
собранная Vite, с палитрой и шрифтами из макета, с состоянием приложения, с
обёрткой моста и с шапкой, которая переключает тип содержимого и разделы. Ленту
и модалки наполняют планы 7–9; здесь они пусты.

**Архитектура:** три слоя с односторонней зависимостью, как записано в решениях:
`styles/` — оформление, `components/` — переиспользуемое, `app/` — сборка; плюс
`state/` и `api/`, которые видит только сборка. Направление
`app → components → styles`, обратно никогда. Держит это не договорённость, а
хук: `<style>` внутри компонента, файл оформления вне `styles/`, импорт вверх по
слоям и цвет мимо палитры отклоняются при записи.

**`state/` — чистые функции, а не реактивные хранилища.** Руны Svelte живут
только в `.svelte` и `.svelte.js`, а логика перехода — «какое состояние следует
за этим» — от реактивности не зависит вовсе. Держать её обычными функциями
значит проверять её обычными тестами, без компилятора и без браузера. Реактивную
ячейку держит сборка, переходы считает `state/`.

**Стек:** Vite 8.2.0, Svelte 5.56.8, `@sveltejs/vite-plugin-svelte` 7.2.0,
Vitest 4.1.10. Шрифты — `@fontsource-variable/roboto` 5.3.0 и
`material-symbols` 0.45.10, оба локальными пакетами. Версии сверены по реестру:
плагин требует `vite ^8` и `svelte ^5.46.4`, Vitest — `vite ^6 || ^7 || ^8`.

## Глобальные ограничения

Действуют на каждую задачу, повторять в них не нужно.

- **Зависит от плана 5.** Мост отвечает на всё, `bridge/serve.py` отдаёт дерево
  `client/dist`, окно поднимается `pipenv run python main.py`.
- **Ни одной ссылки в сеть со страницы.** Ни шрифтов из Google Fonts, ни CDN, ни
  картинок по адресу. Приложение обязано работать офлайн целиком, а страница
  внутри WebView2 не отличает «нет сети» от «нет файла»: макет с сетевым шрифтом
  просто разъедется по метрикам.
- **`docs/design/` — черновик, и зависимости к нему не тянутся ничем.** Ни
  импортом, ни путём, ни `@import`, ни ссылкой из стилей. Оттуда **копируются
  точечно** значения: цвет, кривая, радиус, размер. Копия живёт в чистовике сама
  по себе.
- **Значения макета переносятся точь-в-точь.** Вид уже выверен; «примерно такой
  же отступ» — это другой вид. При расхождении прав макет.
- **Ничего оформительского не придумывается.** Нет значения в макете — это
  вопрос к пользователю, а не повод выбрать самому.
- **`<style>` внутри компонента не бывает вовсе.** Стиль любого блока — свой файл
  в `styles/`, с первого применения, не со второго.
- **Компонент получает всё входными параметрами и сам никуда не ходит.** Залез в
  общее состояние за тем, свёрнута ли карточка, — значит уже знает про сборку.
- **Цвет пишется только в палитре.** По месту — `var(--...)`. Хук отклоняет
  запись файла с цветом мимо палитры, и храповика у этой проверки нет.
- **Компоненты не проверяются.** Проверяются `state/` и `api/` — обычные модули
  без разметки и без браузера. Поддельный браузер с библиотекой разметки весит
  больше, чем ловит.
- **Разметка пишется заново, а не переносится из макета.** Из макета берутся
  имена классов (103 штуки, без столкновений) и значения стилей.
- **Комментарий объясняет неочевидное решение и пишется коротко.**

---

## Файловая структура

```
personal_rating/
├─ client/
│  ├─ index.html                 точка входа Vite
│  ├─ main.js                    монтирует корень
│  ├─ package.json               зависимости и команды
│  ├─ vite.config.js             сборка в dist, псевдонимы слоёв
│  ├─ svelte.config.js
│  ├─ styles/
│  │  ├─ palette.css             58 токенов макета: цвета, ступени, шрифты
│  │  ├─ base.css                сброс, окно, иконки, кромка окна
│  │  ├─ neon.css                неоновая кромка как приём
│  │  ├─ topbar.css              шапка: три зоны
│  │  ├─ search.css              поле поиска
│  │  ├─ seg.css                 переключатель типа
│  │  ├─ tools.css               ряд круглых кнопок
│  │  ├─ view.css                стопка разделов и переход
│  │  └─ snack.css               плашка сообщений
│  ├─ components/
│  │  ├─ Icon.svelte             глиф Material Symbols
│  │  ├─ SearchField.svelte      поле с кнопкой очистки
│  │  ├─ Segmented.svelte        переключатель типа
│  │  ├─ ToolButton.svelte       круглая кнопка шапки
│  │  └─ Snack.svelte            плашка сообщений
│  ├─ state/
│  │  ├─ filters.js              три состояния строки фильтра
│  │  ├─ sorting.js              восемь состояний переключателя
│  │  └─ session.js              что выбрано в приложении
│  ├─ api/
│  │  └─ bridge.js               обёртка над мостом
│  └─ app/
│     ├─ App.svelte              корень: шапка плюс стопка разделов
│     ├─ Topbar.svelte           сборка шапки
│     ├─ SearchScreen.svelte     раздел «Поиск»
│     ├─ LibraryScreen.svelte    «Оценённые» и «Хочу посмотреть»
│     └─ StatsScreen.svelte      раздел «Статистика»
└─ tests/web/
   ├─ filters.test.js            три состояния и складывание
   ├─ sorting.test.js            перебор восьми состояний
   ├─ session.test.js            что чем сбрасывается
   └─ bridge.test.js             номер, отмена, устаревший ответ
```

Правятся и чужие файлы: `.gitignore` (`node_modules/`), `bridge/window.py`
(цвет фона окна сводится с `--bg`), `CLAUDE.md` (вторая цепочка выпуска в
разделе «Окружение»).

**Почему тесты фронта лежат в `tests/web/`, а не рядом с исходниками.** В проекте
уже есть одно место для проверок, и второе правило «где искать тест» стоило бы
дороже, чем короткий относительный путь в конфиге.

---

### Задача 1: Сборка и слои

Первая задача даёт запускаемое: окно показывает не заглушку, а собранную
страницу. Всё остальное в плане прирастает к этому.

**Псевдонимы слоёв обязательны, и не для краткости.** Хук читает `allowed` из
`.claude/clean.json` и разбирает импорты — относительные и по объявленному
псевдониму. Всё, что придумает сборщик сверх этого, он не видит, и граница слоёв
там протекает молча.

**Объявлены они дважды, и это не дубль, а два разных читателя.** `vite.config.js`
говорит сборщику, куда ведёт `$state/`; `.claude/clean.json` говорит хуку, что
`$state/` — это слой `state`. Второй список **не лежит в репозитории**: `.claude/`
закрыт `.gitignore` по решению проекта, и в свежем клоне его нет. Поэтому он
заводится шагом задачи, а не считается данностью.

Разойтись эти два списка могут, и единственный сторож тут — шаг 6, который обязан
проверять **псевдонимом**. Относительным импортом он проходит и с пустыми
псевдонимами, то есть не может упасть на том, ради чего написан.

**Компонентам открыт `state/`** — решение пользователя от 31.07.2026, и оно уже
записано в `allowed`. Правило «компонент в общее состояние не ходит» от этого не
страдает: общего состояния в этом слое нет вовсе, руны живут только в
компонентах, а `state/` считает переходы обычными функциями. `api/` закрыт
по-прежнему: поход через мост — это уже не показ переданного.

**Файлы:**
- Создать: `client/package.json`, `client/vite.config.js`,
  `client/svelte.config.js`, `client/index.html`,
  `client/main.js`, `client/app/App.svelte`
- Изменить: `.gitignore`

**Интерфейсы:**
- Потребляет: `bridge/serve.py` из плана 5 — он отдаёт `client/dist`.
- Отдаёт: команды `npm run build`, `npm run dev`, `npm test`; псевдонимы
  `$styles`, `$components`, `$state`, `$api`.

- [ ] **Шаг 1: Завести пакет**

Из `client/`:

```bash
npm init -y
npm i -D vite@8.2.0 svelte@5.56.8 @sveltejs/vite-plugin-svelte@7.2.0 vitest@4.1.10
```

Версии закреплены, а не `*`: незакреплённый `ruff` уже приезжал в проект другой
мажорной версией и менял то, что означает «чисто». У сборщика фронта цена
ошибки та же.

Привести `client/package.json` к виду:

```json
{
  "name": "personal-rating-web",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  }
}
```

- [ ] **Шаг 2: Настроить сборку**

Создать `client/vite.config.js`:

```js
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

const here = (path) => fileURLToPath(new URL(path, import.meta.url))

export default defineConfig({
  plugins: [svelte()],

  // Псевдонимы объявлены не для краткости: проверка границы слоёв разбирает
  // относительные импорты и объявленные псевдонимы, а всё, что сверх этого
  // придумает сборщик, она не видит.
  resolve: {
    alias: {
      $styles: here('./styles'),
      $components: here('./components'),
      $state: here('./state'),
      $api: here('./api'),
    },
  },

  // Пути относительные: страницу отдаёт свой обработчик, и абсолютный
  // `/assets/...` держался бы только пока корень остаётся корнем.
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },

  // Проверяются `state/` и `api/` — обычные модули без разметки. Поддельный
  // браузер тут не нужен вовсе, а стоил бы ещё одной зависимости и секунд на
  // каждом прогоне.
  test: { include: ['../tests/web/**/*.test.js'], environment: 'node' },
})
```

Создать `client/svelte.config.js`:

```js
export default {}
```

Дописать в `.claude/clean.json`, в раздел `front`, — те же псевдонимы для хука:

```json
    "aliases": {
      "$styles": "styles",
      "$components": "components",
      "$state": "state",
      "$api": "api"
    },
```

Без этого ключа `layers._target` на `$state/...` возвращает `None`, и импорт
пропускается молча — то есть проверка границы слоёв не видит **ни одного**
импорта фронта, потому что все они пишутся псевдонимами. Файл в репозиторий не
входит (`.claude/` закрыт `.gitignore`), поэтому шаг обязателен и в свежем
клоне.

Файл пустой намеренно: препроцессора нет — TypeScript в проекте не берут, а
стили из компонентов вынесены по решению, и обрабатывать в них нечего. Плагин
всё равно ищет этот файл.

- [ ] **Шаг 3: Завести страницу**

Создать `client/index.html`:

```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <title>Personal Rating</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/main.js"></script>
  </body>
</html>
```

Создать `client/main.js`:

```js
import { mount } from 'svelte'

import App from './app/App.svelte'

export default mount(App, { target: document.getElementById('root') })
```

Создать `client/app/App.svelte`:

```svelte
<script>
  // Мост появляется не сразу: pywebview дописывает его после навигации и
  // сообщает об этом событием. До него `window.pywebview` не существует вовсе.
  let ready = $state(Boolean(window.pywebview))
  window.addEventListener('pywebviewready', () => { ready = true })
</script>

<div class="app">
  <p>{ready ? 'мост на месте' : 'жду мост'}</p>
</div>
```

Начальное значение читается сразу, а не только по событию: инъекция идёт на
каждой навигации, и подписка, поставленная после неё, события уже не увидит.

- [ ] **Шаг 4: Закрыть `node_modules` от git**

Дописать в `.gitignore` после раздела «Сборка»:

```
node_modules/
```

- [ ] **Шаг 5: Собрать и запустить**

```bash
cd client && npm run build
cd ../.. && pipenv run python main.py
```

Ожидание: окно открывается, в нём «мост на месте».

- [ ] **Шаг 6: Проверить, что граница слоёв сторожится**

Записать в `client/components/Probe.svelte` строку
`import { call } from '$api/bridge.js'` и попробовать сохранить файл.

Ожидание: **запись отклонена** — компоненту `api/` закрыт: поход через мост это
уже не показ переданного.

**Псевдонимом, а не относительным путём, и это существенно.** Весь код фронта
пишется на `$`-путях, а хук разбирает их только по объявленным псевдонимам.
Проверь относительным импортом — и она пройдёт даже с пустым `aliases`, то есть
не сможет упасть на том, ради чего написана.

Это проверка самого хука, а не кода: фронтовая половина написана против
воображаемого кода, ни одного `.svelte` в проекте до сих пор не было. Первый
слайс проходят с включённым хуком именно затем, чтобы убедиться, что она
работает. После проверки файл удалить.

- [ ] **Шаг 7: Коммит**

```bash
git add client/package.json client/package-lock.json \
        client/vite.config.js client/svelte.config.js \
        client/index.html client/main.js \
        client/app/App.svelte .gitignore
git commit -m "feat: сборка страницы на Vite и Svelte, три слоя"
```

---

### Задача 2: Палитра, база и шрифты

Оформление, от которого зависит всё остальное. Переносится из макета точь-в-точь.

**Шрифты едут локально пакетами.** В макете они приходят ссылкой на Google Fonts
— для приложения, которое обязано работать офлайн, это не годится: без сети
страница молча уедет на запасную цепочку `Segoe UI`, и разъедутся метрики, на
которых стоит замер ширины шапки.

**`FILL` — ось переменного шрифта, а не два начертания.** Правило «контур в
покое, заливка во включённом» держится на `font-variation-settings: 'FILL' 1`, и
`material-symbols` отдаёт именно переменный файл.

**Палитра собирается вся и сразу, а не по мере надобности.** Причина машинная:
хук отклоняет запись любого файла внутри `client/`, где встретился цвет — `#hex`,
`rgba(`, даже слово `black`, — и храповика у этой проверки нет. Значит первый же
файл оформления с литералом просто не запишется. Поэтому ступени белого и
чёрного перенесены сюда все двадцать шесть, хотя потребители у большинства
появятся только в планах 7–9: это не «на всякий случай», а единственный способ
вообще написать те файлы.

**Ступени названы числом, а не ролью, и это решение, а не лень.** Одна и та же
`rgba(255,255,255,.09)` служит в макете то границей окна, то подложкой кнопки,
то разделителем строки; роль в имени была бы неправдой в половине мест.
Значения перенесены точь-в-точь — меняется только имя.

**Файлы:**
- Создать: `client/styles/palette.css`, `base.css`, `neon.css`
- Изменить: `client/main.js`, `bridge/window.py`

**Интерфейсы:**
- Потребляет: значения из `docs/design/styles/tokens.css`, `base.css`,
  `neon.css` и из инлайнового стиля `docs/design/index.html:13-72`.
- Отдаёт: переменные `--primary`, `--bg`, `--error`, `--glass`, `--glass-error`,
  `--surface-pop`, `--opaque`, `--score-1`…`--score-10`, `--accent-movie`,
  `--accent-series`, `--accent-game`, `--tint-02`…`--tint-85` (двадцать две
  ступени), `--shade-25`…`--shade-60` (четыре), `--text`, `--text-bright`,
  `--text-dim`, `--r-card`, `--r-full`, `--font` и шесть типографических ролей;
  классы `.app`, `.material-symbols-outlined`, `.neon`.

- [ ] **Шаг 1: Поставить шрифты**

Из `client/`:

```bash
npm i @fontsource-variable/roboto@5.3.0 material-symbols@0.45.10
```

Оба — обычные зависимости, а не `-D`: их файлы уезжают в сборку.

- [ ] **Шаг 2: Перенести палитру**

Создать `client/styles/palette.css`:

```css
/* Единственное место, где есть цвет. По месту пишется только var(). */

/* Без регистрации браузер не интерполирует переменную, и акцент менялся бы
   скачком вместо перетекания. */
@property --primary {
  syntax: '<color>';
  inherits: true;
  initial-value: #84e310;
}

:root {
  /* Перетекание акцента; на какой цвет — ставит переключатель типа. */
  transition: --primary .35s;

  --bg:                 #0a0a0a;
  --fill-primary-hover: color-mix(in srgb, var(--primary) 18%, transparent);
  --error:              #ff4a45;

  --glass-error:        rgba(39,15,15,.55);
  --surface-pop:        rgba(14,16,19,.98);
  --glass:              rgba(6,7,9,.72);

  /* Непрозрачная точка градиента-маски. Цвет в маске не участвует вовсе —
     читается только альфа, — но написанный по месту он всё равно цвет. */
  --opaque:             #000;

  /* Цвет закреплён за значением и одинаков везде — в фильтре, на карточках, в
     статистике. Имя собирается строкой: var(--score-${n}). */
  --score-1:  #F44336;
  --score-2:  #FF5722;
  --score-3:  #FF9800;
  --score-4:  #FFC107;
  --score-5:  #FFEB3B;
  --score-6:  #CDDC39;
  --score-7:  #8BC34A;
  --score-8:  #4CAF50;
  --score-9:  #00BCD4;
  --score-10: #2196F3;

  --text:               rgba(255,255,255,.90);
  --text-bright:        #ffffff;
  --text-dim:           rgba(255,255,255,.32);

  /* Акцент типа содержимого. Переключатель ставит `--primary` одним из трёх;
     литералами в разметке им делать нечего — цвет живёт здесь. */
  --accent-movie:       #84e310;
  --accent-series:      #3b9eff;
  --accent-game:        #FFC107;

  /* Белое и чёрное поверх тёмного фона. Названы ступенью, а не ролью, и это
     не лень: одна и та же ступень служит то границей, то подложкой, то
     приглушённым текстом, и роль в имени была бы неправдой в половине мест.
     Значения перенесены из макета точь-в-точь — меняется только имя. */
  --tint-02:  rgba(255,255,255,.02);
  --tint-035: rgba(255,255,255,.035);
  --tint-05:  rgba(255,255,255,.05);
  --tint-06:  rgba(255,255,255,.06);
  --tint-07:  rgba(255,255,255,.07);
  --tint-09:  rgba(255,255,255,.09);
  --tint-10:  rgba(255,255,255,.1);
  --tint-14:  rgba(255,255,255,.14);
  --tint-16:  rgba(255,255,255,.16);
  --tint-18:  rgba(255,255,255,.18);
  --tint-22:  rgba(255,255,255,.22);
  --tint-25:  rgba(255,255,255,.25);
  --tint-28:  rgba(255,255,255,.28);
  --tint-30:  rgba(255,255,255,.3);
  --tint-34:  rgba(255,255,255,.34);
  --tint-35:  rgba(255,255,255,.35);
  --tint-40:  rgba(255,255,255,.4);
  --tint-45:  rgba(255,255,255,.45);
  --tint-55:  rgba(255,255,255,.55);
  --tint-75:  rgba(255,255,255,.75);
  --tint-80:  rgba(255,255,255,.8);
  --tint-85:  rgba(255,255,255,.85);

  --shade-25: rgba(0,0,0,.25);
  --shade-32: rgba(0,0,0,.32);
  --shade-55: rgba(0,0,0,.55);
  --shade-60: rgba(0,0,0,.6);

  --r-card:             20px;
  --r-full:             999px;

  --font:       "Roboto Variable", "Segoe UI", system-ui, sans-serif;

  --title-l:    400 22px/28px var(--font);
  --title-s:    500 14px/20px var(--font);
  --body-l:     400 16px/24px var(--font);
  --body-m:     400 14px/20px var(--font);
  --label-l:    500 14px/20px var(--font);
  --label-m:    500 12px/16px var(--font);
}
```

Единственное расхождение с макетом — имя семейства: `@fontsource-variable`
объявляет `Roboto Variable`, а не `Roboto`. Запасная цепочка та же.

**`--lime` из макета не переносится.** Это алиас `var(--primary)` с пятью
обращениями из одного блока — два имени у одного значения; в чистовике блок
берёт `--primary` напрямую.

- [ ] **Шаг 3: Перенести базу и кромку окна**

Создать `client/styles/base.css`. Это `docs/design/styles/base.css` плюс
кромка окна из инлайнового стиля (`index.html:23-56`), с одной правкой:
`min-width` у `body` не ставим — минимум окна держит `bridge/window.py`.

```css
*, *::before, *::after { box-sizing: border-box }

/* display:none у атрибута hidden приходит из стилей браузера, и любой display
   в классе его перебивает. Возвращаем атрибуту приоритет. */
[hidden] { display: none !important }

html, body { height: 100% }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: var(--body-m);
  -webkit-font-smoothing: antialiased;

  /* Это приложение, а не браузер: без выделения текста и без резинового
     отскока при прокрутке. */
  overscroll-behavior: none;
  user-select: none;
}

:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 3px;
}

::selection {
  background: var(--fill-primary-hover);
  color: var(--text-bright);
}

.material-symbols-outlined {
  font-family: "Material Symbols Outlined";
  font-weight: normal;
  font-style: normal;
  font-size: 24px;
  line-height: 1;
  display: inline-block;
  direction: ltr;
  white-space: nowrap;
  word-wrap: normal;
  font-feature-settings: "liga";
  font-variation-settings: 'FILL' 0;
  transition: font-variation-settings .18s;
}

/* Включённая кнопка показывает закрашенный вариант иконки, выключенная —
   контурный. Одно правило на всё приложение. */
.is-active > .material-symbols-outlined,
.is-on > .material-symbols-outlined {
  font-variation-settings: 'FILL' 1;
}

.app {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;

  /* Тихое свечение от верхней кромки — стеклу есть что преломлять. */
  background: radial-gradient(
    ellipse at 50% 5%,
    color-mix(in srgb, var(--primary) 3%, transparent) 0%,
    transparent 45%);
}

.app::before,
.app::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
}

/* Нить во всю ширину окна, гаснущая к краям. */
.app::before {
  top: 0;
  height: 1px;
  z-index: 2;
  background: linear-gradient(90deg, transparent,
    var(--primary) 22%, var(--primary) 78%, transparent);
  box-shadow: 0 0 8px color-mix(in srgb, var(--primary) 55%, transparent);
}

/* Гало центром сидит на самой кромке, поэтому разлив уходит вниз, на страницу. */
.app::after {
  top: -8px;
  height: 16px;
  z-index: 1;
  border-radius: 50%;
  background: color-mix(in srgb, var(--primary) 38%, transparent);
  filter: blur(12px);
}

.app__main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- [ ] **Шаг 4: Перенести приём неоновой кромки**

Создать `client/styles/neon.css` — перенос `docs/design/styles/neon.css`
без правок:

```css
/* Общий приём: полоса по верхней кромке, гаснущая к краям, гало под ней и
   свечение текста. Цвет из --neon, высоту гало из --halo-h ставит тот, кто
   применяет класс. */

.neon {
  --halo-h: 22px;

  position: relative;
  color: var(--neon);

  text-shadow:
    0 0 6px  color-mix(in srgb, var(--neon) 55%, transparent),
    0 0 16px color-mix(in srgb, var(--neon) 30%, transparent);
}

/* Кромка идёт по скруглению, а не прямой чертой поверх него. Гашение к краям
   делает маска — она съедает и линию, и её свечение разом, потому что
   drop-shadow считает по прозрачности источника. */
.neon::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;

  border-radius: inherit;
  border-top: 1px solid var(--neon);
  mask-image: linear-gradient(90deg, transparent, var(--opaque) 50%, transparent);
  filter: drop-shadow(0 0 3px var(--neon)) drop-shadow(0 0 9px var(--neon));
}

/* Гало — отдельная подложка, а не размытие кромки: маска обрезала бы разлив по
   краю блока. */
.neon::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: calc(var(--halo-h) / -2);
  height: var(--halo-h);
  z-index: 1;
  pointer-events: none;

  background: radial-gradient(
    60% 50% at 50% 50%,
    color-mix(in srgb, var(--neon) 24%, transparent) 0%,
    transparent 72%);
}
```

**В макете этот приём написан дважды** — своей копией для кромки окна в
инлайновом стиле и файлом `neon.css` для плашки. Копии остаются двумя разными
вещами и в чистовике, но не потому, что их поленились свести: у окна нить идёт
во всю ширину и гало уходит вниз на страницу, у плашки нить идёт по скруглению
капсулы, а гало сидит над ней. Общего у них только слово «свечение».

- [ ] **Шаг 5: Подключить**

В `client/main.js` — импорты до монтирования. Порядок обязателен:
палитра первой, иначе `base.css` возьмёт неопределённые переменные.

```js
import '@fontsource-variable/roboto'
import 'material-symbols/outlined.css'
import { mount } from 'svelte'

import App from './app/App.svelte'
import '$styles/palette.css'
import '$styles/base.css'
import '$styles/neon.css'

export default mount(App, { target: document.getElementById('root') })
```

- [ ] **Шаг 6: Свести цвет окна с палитрой**

В `bridge/window.py` цвет фона окна стоит литералом — это цвет до отрисовки
страницы, и разъехавшись с `--bg`, он дал бы вспышку другого оттенка при каждом
запуске. Поставить `#0a0a0a` и записать рядом, откуда значение.

- [ ] **Шаг 7: Собрать и посмотреть**

```bash
cd client && npm run build
cd ../.. && pipenv run python main.py
```

Ожидание: фон почти чёрный, по верхней кромке окна — салатовая нить со
свечением, гаснущая к краям; текст рисуется Roboto, а не системным шрифтом.

**Проверить, что шрифт местный:** запустить с `PR_DEBUG=1`, открыть инспектор,
вкладку сети — запросов на `fonts.googleapis.com` быть не должно ни одного.

- [ ] **Шаг 8: Коммит**

```bash
git add client/styles/ client/main.js client/package.json \
        client/package-lock.json bridge/window.py
git commit -m "feat: палитра, база и локальные шрифты из макета"
```

---

### Задача 3: Состояние приложения

Три модуля чистых функций. Здесь живёт почти вся логика фронта, и здесь же почти
все его проверки: ни разметки, ни браузера, ни моста.

**Что чем сбрасывается — записано в спеке разделов, и переписывать это правило
сюда нельзя своими словами.** Смена типа содержимого сбрасывает все фильтры;
смена раздела не трогает ничего; свёрнутость — тумблер всего приложения, а не
настройка раздела; сортировка живёт сеанс раздела.

**Три состояния строки фильтра: не выбран, включён, исключён.** Включённые
внутри признака складываются по «или», между признаками — по «и», исключённые
вычитаются последними. Само сложение делает база; здесь строка раскладывается на
два кортежа.

**Файлы:**
- Создать: `client/state/filters.js`, `sorting.js`, `session.js`
- Создать: `tests/web/filters.test.js`, `sorting.test.js`, `session.test.js`

**Интерфейсы:**
- Потребляет: ничего.
- Отдаёт: `EMPTY`, `cycled(filters, field, id)`, `marked(filters, field, id)`,
  `chosen(filters)`, `isEmpty(filters)`, `passes(view, filters)`;
  `SORT_STATES`, `ADDED_AT`, `cycleOf(section)`,
  `nextSort(section, position)`, `stateAt(section, position)`, `orderOf(index)`,
  `orderFor(section, position)`; `newSession()`,
  `withKind(session, kind)`, `withSection(session, section)`,
  `withCollapsed(session, collapsed)`.

- [ ] **Шаг 1: Написать падающие тесты**

Создать `tests/web/filters.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { EMPTY, chosen, cycled, isEmpty, marked, passes } from '$state/filters.js'

describe('строка фильтра', () => {
  it('перебирает три состояния по кругу', () => {
    const on = cycled(EMPTY, 'tags', 3)
    const excluded = cycled(on, 'tags', 3)
    const off = cycled(excluded, 'tags', 3)

    expect(chosen(on).tag_ids).toEqual([3])
    expect(chosen(excluded).excluded_tag_ids).toEqual([3])
    expect(isEmpty(off)).toBe(true)
  })

  it('исключённое перестаёт быть включённым', () => {
    // Строка не может быть и включена, и исключена разом: иначе запрос сложил
    // бы «покажи драмы» с «ни одной драмы» и вернул пустоту всегда.
    const excluded = cycled(cycled(EMPTY, 'genres', 7), 'genres', 7)

    expect(chosen(excluded).genre_ids).toEqual([])
    expect(chosen(excluded).excluded_genre_ids).toEqual([7])
  })

  it('разные признаки не мешают друг другу', () => {
    // Между признаками сложение по «и», и путаница полями дала бы тег в
    // жанрах — запрос при этом не упал бы, а просто вернул не то.
    const both = cycled(cycled(EMPTY, 'tags', 3), 'genres', 7)
    const request = chosen(both)

    expect(request.tag_ids).toEqual([3])
    expect(request.genre_ids).toEqual([7])
    expect(request.excluded_tag_ids).toEqual([])
  })

  it('складывает включённые внутри признака', () => {
    const two = cycled(cycled(EMPTY, 'scores', 9), 'scores', 10)
    expect(chosen(two).scores.toSorted()).toEqual([9, 10])
  })

  it('пустой набор — это отсутствие фильтра, а не пустой признак', () => {
    // Спека: «страница шлёт только то, что человек тронул».
    expect(isEmpty(EMPTY)).toBe(true)
    expect(chosen(EMPTY)).toEqual({
      tag_ids: [], genre_ids: [], scores: [],
      excluded_tag_ids: [], excluded_genre_ids: [], excluded_scores: [],
    })
  })

  it('знает, что фильтр применён — по нему горит кнопка в шапке', () => {
    expect(isEmpty(cycled(EMPTY, 'tags', 3))).toBe(false)
  })
})

describe('отсев выдачи поиска', () => {
  // Спросить источник с фильтром нечем: у TMDB и магазинов нет ни наших тегов,
  // ни наших оценок. Ответ приходит целиком, и уже показанное отсеивается по
  // тем же признакам, что и лента.
  const view = (fields) => ({ genres: [], tags: [], rating: null, ...fields })

  it('без фильтра проходит всё', () => {
    expect(passes(view({}), EMPTY)).toBe(true)
  })

  it('жанр у кандидата есть, и по нему отсев работает', () => {
    // Жанры разворачиваются справочником прямо в выдаче — единственный признак
    // фильтра, который у кандидата вообще есть.
    const only = cycled(EMPTY, 'genres', 7)

    expect(passes(view({ genres: [{ id: 7 }] }), only)).toBe(true)
    expect(passes(view({ genres: [{ id: 9 }] }), only)).toBe(false)
  })

  it('внутри признака складывает по «или»', () => {
    const two = cycled(cycled(EMPTY, 'genres', 7), 'genres', 9)
    expect(passes(view({ genres: [{ id: 9 }] }), two)).toBe(true)
  })

  it('между признаками складывает по «и»', () => {
    const both = cycled(cycled(EMPTY, 'genres', 7), 'tags', 3)

    expect(passes(view({ genres: [{ id: 7 }], tags: [{ id: 3 }] }), both)).toBe(true)
    expect(passes(view({ genres: [{ id: 7 }], tags: [] }), both)).toBe(false)
  })

  it('исключённое вычитается последним и сильнее включённого', () => {
    // «Показать всё, кроме ужасов» — частый запрос; «показать ужасы, которые я
    // же и исключил» смысла не имеет.
    const drama = cycled(EMPTY, 'genres', 7)
    const noHorror = cycled(cycled(drama, 'genres', 9), 'genres', 9)

    expect(passes(view({ genres: [{ id: 7 }, { id: 9 }] }), noHorror)).toBe(false)
  })

  it('фильтр по тегу прячет всё, чего ещё нет в библиотеке', () => {
    // У кандидата нет ни тегов, ни оценки: они держатся за `item_id`, а выдача
    // поиска в базу не попадает никогда.
    const tagged = cycled(EMPTY, 'tags', 3)
    expect(passes(view({ tags: [] }), tagged)).toBe(false)
  })

  it('фильтр по оценке смотрит на округлённую вниз', () => {
    // У игр оценка — среднее трёх шкал: 7.33 попадает в семёрку, как и везде.
    const seven = cycled(EMPTY, 'scores', 7)
    expect(passes(view({ rating: { score: 7.33 } }), seven)).toBe(true)
    expect(passes(view({ rating: null }), seven)).toBe(false)
  })
})

describe('метка на карточке', () => {
  it('переключает два состояния, а не три', () => {
    // Исключить с карточки нечем: третье состояние живёт только в модалке.
    const on = marked(EMPTY, 'genres', 7)
    expect(chosen(on).genre_ids).toEqual([7])

    const off = marked(on, 'genres', 7)
    expect(isEmpty(off)).toBe(true)
  })

  it('не проводит метку через исключение по дороге', () => {
    // Если бы клик по метке шёл тем же перебором, второе нажатие означало бы
    // «ни одного такого» — то есть скрывало бы карточку, с которой нажали.
    const twice = marked(marked(EMPTY, 'genres', 7), 'genres', 7)
    expect(chosen(twice).excluded_genre_ids).toEqual([])
  })

  it('снимает исключение, выставленное в модалке', () => {
    // Метка знает два состояния, и включённой она обязана стать из любого:
    // иначе исключённый в модалке жанр с карточки было бы не включить.
    const excluded = cycled(cycled(EMPTY, 'genres', 7), 'genres', 7)
    const on = marked(excluded, 'genres', 7)

    expect(chosen(on).genre_ids).toEqual([7])
    expect(chosen(on).excluded_genre_ids).toEqual([])
  })
})
```

Создать `tests/web/sorting.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { ADDED_AT, SORT_STATES, cycleOf, nextSort, orderFor, orderOf, stateAt }
  from '$state/sorting.js'

const keysOf = (section) =>
  cycleOf(section).map((index) => SORT_STATES[index].key)

describe('переключатель сортировки', () => {
  it('в оценённых восемь состояний, в отложенном четыре', () => {
    expect(cycleOf('rated')).toHaveLength(8)
    expect(cycleOf('wishlist')).toHaveLength(4)
  })

  it('в отложенном осмысленны только два критерия', () => {
    // Своей оценки у неоценённого не бывает, времени оценки тем более, а дата
    // выхода в списке дел ни о чём не говорит.
    expect(new Set(keysOf('wishlist'))).toEqual(new Set([ADDED_AT, 'title']))
  })

  it('дату добавления в оценённых не встретить', () => {
    // Девятое состояние понадобилось бы ровно одному разделу.
    expect(keysOf('rated')).not.toContain(ADDED_AT)
  })

  it('соседи — две стороны одного критерия, и это верно в обоих разделах', () => {
    // Перебор обязан сначала перевернуть направление и лишь потом сменить
    // критерий: иначе он читается как случайный список.
    for (const section of ['rated', 'wishlist']) {
      const cycle = cycleOf(section)
      for (let at = 0; at < cycle.length; at += 2) {
        const first = orderFor(section, at)
        const second = orderFor(section, at + 1)

        expect(second.key).toBe(first.key)
        expect(second.descending).toBe(!first.descending)
      }
    }
  })

  it('нетронутый переключатель даёт первое состояние своего набора', () => {
    expect(orderFor('rated', null)).toEqual({ key: 'score', descending: true })
    expect(orderFor('wishlist', null)).toEqual({ key: ADDED_AT, descending: true })
  })

  it('замыкается по своему набору, а не по общей таблице', () => {
    // В отложенном круг вчетверо короче: перебор по восьми увёл бы его в
    // состояния, которых у раздела нет.
    let at = 0
    for (let step = 0; step < 4; step += 1) at = nextSort('wishlist', at)
    expect(at).toBe(0)

    at = 0
    for (let step = 0; step < 8; step += 1) at = nextSort('rated', at)
    expect(at).toBe(0)
  })

  it('не повторяет ни одного состояния внутри набора', () => {
    for (const section of ['rated', 'wishlist']) {
      const seen = cycleOf(section).map((_, at) => {
        const { key, descending } = orderFor(section, at)
        return `${key}:${descending}`
      })
      expect(new Set(seen).size).toBe(cycleOf(section).length)
    }
  })

  it('каждое состояние объясняет себя словами', () => {
    // Подпись уезжает в title кнопки: перебор без подсветки иначе не прочесть.
    for (const state of SORT_STATES) {
      expect(state.label.length).toBeGreaterThan(0)
      expect(state.icon.length).toBeGreaterThan(0)
      expect(state.dir).toMatch(/^arrow_(up|down)ward$/)
    }
  })

  it('кнопка берёт вид из состояния своего раздела', () => {
    // Позиция 0 в двух разделах — разные состояния, и глиф обязан различаться.
    expect(stateAt('wishlist', 0).key).toBe(ADDED_AT)
    expect(stateAt('rated', 0).key).toBe('score')
  })
})
```

Создать `tests/web/session.test.js`:

```js
import { describe, expect, it } from 'vitest'

import { EMPTY, cycled, isEmpty } from '$state/filters.js'
import { newSession, withCollapsed, withKind, withSection } from '$state/session.js'

const filtered = () => ({ ...newSession(), filters: cycled(EMPTY, 'tags', 3) })

describe('состояние приложения', () => {
  it('открывается на поиске и на фильмах', () => {
    // При запуске карточек нет, и первый раздел — поиск.
    const session = newSession()
    expect(session.section).toBe('search')
    expect(session.kind).toBe('movie')
  })

  it('смена типа сбрасывает все фильтры', () => {
    // Наборы тегов у трёх типов независимы, а жанров наборов два — фильтр
    // после переключения указывал бы на строки, которых в новом наборе нет.
    const after = withKind(filtered(), 'game')

    expect(after.kind).toBe('game')
    expect(isEmpty(after.filters)).toBe(true)
  })

  it('смена типа на тот же самый ничего не сбрасывает', () => {
    // Щелчок по уже включённой кнопке — не смена, и терять из-за него
    // выставленный фильтр человек не согласится.
    const before = filtered()
    expect(withKind(before, before.kind)).toBe(before)
  })

  it('смена раздела фильтры не трогает', () => {
    // Иначе отфильтрованную гистограмму не увидеть никогда.
    const after = withSection(filtered(), 'stats')

    expect(after.section).toBe('stats')
    expect(isEmpty(after.filters)).toBe(false)
  })

  it('свёрнутость переживает смену раздела', () => {
    // Это тумблер всего приложения, а не настройка раздела.
    const collapsed = withCollapsed(newSession(), true)
    expect(withSection(collapsed, 'wishlist').collapsed).toBe(true)
  })

  it('свёрнутость переживает и смену типа', () => {
    const collapsed = withCollapsed(newSession(), true)
    expect(withKind(collapsed, 'series').collapsed).toBe(true)
  })

  it('сортировка живёт сеанс раздела', () => {
    // Ушёл с раздела — переключатель вернулся к порядку по умолчанию.
    const touched = { ...newSession(), section: 'wishlist', sort: 5 }
    expect(withSection(touched, 'rated').sort).toBe(null)
  })
})
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

```bash
cd client && npm test
```

Ожидание: FAIL, `Cannot find module '$state/filters.js'`.

- [ ] **Шаг 3: Написать фильтры**

Создать `client/state/filters.js`:

```js
/** Три состояния строки фильтра: не выбран, включён, исключён. */

// Имена полей — контракт с мостом: он раскладывает их прямо в `Filters`.
export const FIELDS = ['tags', 'genres', 'scores']

export const EMPTY = { on: { tags: [], genres: [], scores: [] },
                       ex: { tags: [], genres: [], scores: [] } }

/** Следующее состояние строки: пусто → включено → исключено → пусто. */
export function cycled(filters, field, id) {
  const on = filters.on[field].includes(id)
  const ex = filters.ex[field].includes(id)

  return {
    on: { ...filters.on, [field]: on ? without(filters.on[field], id)
                                     : ex ? filters.on[field]
                                          : [...filters.on[field], id] },
    // Включённое и исключённое разом дало бы «покажи драмы» вместе с «ни одной
    // драмы», то есть пустоту всегда.
    ex: { ...filters.ex, [field]: on ? [...filters.ex[field], id]
                                     : without(filters.ex[field], id) },
  }
}

/** То, что уезжает мосту: шесть кортежей, как их ждёт `Filters`. */
export function chosen(filters) {
  return {
    tag_ids: filters.on.tags,
    genre_ids: filters.on.genres,
    scores: filters.on.scores,
    excluded_tag_ids: filters.ex.tags,
    excluded_genre_ids: filters.ex.genres,
    excluded_scores: filters.ex.scores,
  }
}

/** Метка на карточке: два состояния вместо трёх. Включён и не активен —
 *  исключить с карточки нечем.
 *
 *  Отдельно от `cycled` не по прихоти: пройди метка тем же перебором, второе
 *  нажатие означало бы «ни одного такого», то есть скрывало бы ту самую
 *  карточку, с которой нажали. */
export function marked(filters, field, id) {
  const on = filters.on[field].includes(id)
  return {
    on: { ...filters.on,
          [field]: on ? without(filters.on[field], id)
                      : [...filters.on[field], id] },
    // Включённой метка становится из любого состояния: иначе исключённый в
    // модалке жанр с карточки было бы не включить.
    ex: { ...filters.ex, [field]: without(filters.ex[field], id) },
  }
}

/** По этому горит кнопка фильтра в шапке. */
export function isEmpty(filters) {
  return FIELDS.every((field) => !filters.on[field].length
                              && !filters.ex[field].length)
}

/** Проходит ли карточка фильтр. Нужно поиску: спросить источник с фильтром
 *  нечем — у TMDB и магазинов нет ни наших тегов, ни наших оценок, — поэтому
 *  ответ приходит целиком, а отсев идёт здесь.
 *
 *  В разделах библиотеки этим не пользуются: там то же самое делает база, и
 *  делает лучше — она не тащит через границу то, что всё равно скроют. */
export function passes(view, filters) {
  return FIELDS.every((field) => {
    const has = ownedBy(view, field)
    if (filters.ex[field].some((id) => has.includes(id))) return false
    if (!filters.on[field].length) return true
    return filters.on[field].some((id) => has.includes(id))
  })
}

/** Чем карточка отвечает на каждый признак. У кандидата поиска есть только
 *  жанры: теги и оценка держатся за `item_id`, а его у него нет. */
function ownedBy(view, field) {
  if (field === 'genres') return view.genres.map((one) => one.id)
  if (field === 'tags') return view.tags.map((one) => one.id)
  // Дробные оценки округляются вниз — правило общее для всего показа.
  const score = view.rating?.score
  return score ? [Math.floor(score)] : []
}

const without = (ids, id) => ids.filter((each) => each !== id)
```

- [ ] **Шаг 4: Написать сортировку**

Создать `client/state/sorting.js`:

```js
/** Восемь состояний переключателя: четыре критерия, каждый в две стороны. */

// Есть только в переборе «Хочу посмотреть»: в «Оценённых» девятое состояние
// понадобилось бы ровно одному разделу.
export const ADDED_AT = 'added_at'

// Глифы и подписи взяты из макета целиком. Направление показано стрелкой в
// углу кнопки, а сам критерий — основным глифом: подсветки у перебора нет.
//
// Последняя пара — дата добавления — в макете отсутствует: там перебор был на
// восемь состояний. Глиф у неё назван здесь впервые и подлежит сверке.
export const SORT_STATES = [
  { key: 'score',    down: true,  icon: 'star',          dir: 'arrow_downward', label: 'По оценке, сначала высокие' },
  { key: 'score',    down: false, icon: 'star',          dir: 'arrow_upward',   label: 'По оценке, сначала низкие' },
  { key: 'rated_at', down: true,  icon: 'history',       dir: 'arrow_downward', label: 'По времени оценки, сначала свежие' },
  { key: 'rated_at', down: false, icon: 'history',       dir: 'arrow_upward',   label: 'По времени оценки, сначала давние' },
  { key: 'year',     down: true,  icon: 'event',         dir: 'arrow_downward', label: 'По дате выхода, сначала новые' },
  { key: 'year',     down: false, icon: 'event',         dir: 'arrow_upward',   label: 'По дате выхода, сначала старые' },
  { key: 'title',    down: true,  icon: 'sort_by_alpha', dir: 'arrow_downward', label: 'По алфавиту, А → Я' },
  { key: 'title',    down: false, icon: 'sort_by_alpha', dir: 'arrow_upward',   label: 'По алфавиту, Я → А' },
  { key: ADDED_AT,   down: true,  icon: 'bookmark_added', dir: 'arrow_downward', label: 'По дате добавления, сначала свежие' },
  { key: ADDED_AT,   down: false, icon: 'bookmark_added', dir: 'arrow_upward',   label: 'По дате добавления, сначала давние' },
]

// Какие состояния перебирает раздел. В отложенном осмысленны только два
// критерия: своей оценки у неоценённого не бывает, времени оценки тем более, а
// дата выхода в списке дел ни о чём не говорит.
//
// Хранится позиция в наборе своего раздела, а не номер строки таблицы: при
// смене раздела переключатель и так сбрасывается, а позиция читается глазами.
const CYCLES = {
  wishlist: [8, 9, 6, 7],
  rated: [0, 1, 2, 3, 4, 5, 6, 7],
}

export const cycleOf = (section) => CYCLES[section] ?? CYCLES.rated

export const nextSort = (section, position) =>
  (position + 1) % cycleOf(section).length

/** Состояние переключателя раздела: глиф, стрелка, подпись. */
export const stateAt = (section, position) =>
  SORT_STATES[cycleOf(section)[position]]

/** То, что уезжает мосту полем `order`. */
export function orderOf(index) {
  const state = SORT_STATES[index]
  return { key: state.key, descending: state.down }
}

/** Порядок раздела: `position` — состояние переключателя или `null`, если он не
 *  тронут. Нетронутый значит первое состояние своего набора: в отложенном
 *  свежие сверху, в оценённых высокие сверху. */
export function orderFor(section, position) {
  return orderOf(cycleOf(section)[position ?? 0])
}
```

- [ ] **Шаг 5: Написать состояние**

Создать `client/state/session.js`:

```js
/** Что выбрано в приложении и что чем сбрасывается. */

import { EMPTY } from '$state/filters.js'

export const SECTIONS = ['search', 'rated', 'wishlist', 'stats']

/** При запуске карточек нет: приложение открывается на поиске. */
export const newSession = () => ({
  kind: 'movie',
  section: 'search',
  filters: EMPTY,
  // `null` значит «переключатель не тронут», и тогда действует порядок по
  // умолчанию раздела. Нулём это не записать: ноль — законное состояние.
  sort: null,
  collapsed: false,
})

/** Смена типа сбрасывает все фильтры: наборы тегов у трёх типов независимы, а
 *  жанров наборов два, и фильтр после переключения указывал бы в пустоту. */
export function withKind(session, kind) {
  if (kind === session.kind) return session
  return { ...session, kind, filters: EMPTY }
}

/** Разделы фильтры не трогают: иначе отфильтрованную гистограмму не увидеть
 *  никогда. А вот сортировка живёт ровно сеанс раздела. */
export function withSection(session, section) {
  if (section === session.section) return session
  return { ...session, section, sort: null }
}

/** Тумблер всего приложения, а не настройка раздела. */
export const withCollapsed = (session, collapsed) => ({ ...session, collapsed })
```

- [ ] **Шаг 6: Прогнать и увидеть зелёное**

```bash
cd client && npm test
```

Ожидание: PASS, 32 теста.

- [ ] **Шаг 7: Коммит**

```bash
git add client/state/ tests/web/
git commit -m "feat: состояние приложения — фильтры, сортировка, что чем сбрасывается"
```

---

### Задача 4: Обёртка моста

Единственное место страницы, которое знает про `window.pywebview`. Делает
четыре вещи: ждёт готовности моста, нумерует операции, отбрасывает устаревшие
ответы и разворачивает `{"ok"}` / `{"fail"}`.

**Номер свой, а не мостовой.** Мосту номер нужен, только чтобы было что отменить;
странице — чтобы не дать старому ответу затереть новый. Счётчик один на всё
приложение: два номера из разных мест столкнулись бы в таблице задач моста.

**Отмена — это обещание, а не просьба.** Ушли с раздела — начатое отменяется, и
довод замеренный: квоты агрегаторов конечны, и двадцать бро́шенных запросов
прокрутки тратят их так же, как двадцать нужных.

**Своего срока у обёртки нет.** Его держит мост: 60 секунд, сторож от
невозвращающегося вызова. Второй срок здесь означал бы два места, где решают
одно и то же, и разъехались бы они молча.

**Файлы:**
- Создать: `client/api/bridge.js`
- Создать: `tests/web/bridge.test.js`

**Интерфейсы:**
- Потребляет: поверхность моста из плана 5 — `library`, `marks`, `refs`, `feed`,
  `search`, `world`, `covers`, `cancel(ops)`.
- Отдаёт: `ready()`, `call(path, ...args)`, `numbered(path, ...args)`,
  `lastOp(channel)`, `cancel(ops)`, `Failed`. Настройки вызова — последним
  доводом-объектом: `channel` (что вытесняет само себя), `op` (чужой номер для
  второго шага), `ops` (куда положить номер, чтобы было чем отменить).

- [ ] **Шаг 1: Написать падающий тест**

Создать `tests/web/bridge.test.js`:

```js
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { Failed, call, cancel, lastOp, numbered, ready } from '$api/bridge.js'

/** Поддельный мост: отвечает тем, что положили, и записывает, о чём спросили. */
function fake(answers = {}) {
  const asked = []
  const api = {
    cancel: (ops) => { asked.push(['cancel', ops]); return { ok: null } },
  }
  for (const [path, answer] of Object.entries(answers)) {
    const [domain, method] = path.split('.')
    api[domain] ??= {}
    api[domain][method] = (...args) => {
      asked.push([path, args])
      return typeof answer === 'function' ? answer(...args) : answer
    }
  }
  globalThis.window = { pywebview: { api }, addEventListener: () => {} }
  return asked
}

beforeEach(() => { vi.restoreAllMocks() })

describe('обёртка моста', () => {
  it('разворачивает удачный ответ', async () => {
    fake({ 'marks.tags': { ok: [{ id: 1, name: 'драма' }] } })

    await expect(call('marks.tags', 'movie')).resolves.toEqual([
      { id: 1, name: 'драма' },
    ])
  })

  it('отказ операции превращается в исключение с родом', async () => {
    // Ловить семь исключений бэкенда в разметке нельзя, а один род — можно.
    fake({ 'marks.rename_tag': { fail: 'tag-exists', detail: 'драма' } })

    await expect(call('marks.rename_tag', 3, 'драма'))
      .rejects.toThrow(Failed)
    await call('marks.rename_tag', 3, 'драма').catch((error) => {
      expect(error.kind).toBe('tag-exists')
      expect(error.detail).toBe('драма')
    })
  })

  it('нумерованная операция получает свой номер первым доводом', async () => {
    const asked = fake({ 'world.enrich': { ok: [] } })

    await numbered('world.enrich', 12, 'movie')

    const [path, args] = asked[0]
    expect(path).toBe('world.enrich')
    expect(typeof args[0]).toBe('number')
    expect(args.slice(1)).toEqual([12, 'movie'])
  })

  it('номера не повторяются', async () => {
    const asked = fake({ 'world.enrich': { ok: [] } })

    await numbered('world.enrich', 1, 'movie')
    await numbered('world.enrich', 2, 'movie')

    expect(asked[0][1][0]).not.toBe(asked[1][1][0])
  })

  it('второй шаг зовётся тем же номером, что и первый', async () => {
    // Без этого мостовая память второй шаг не узнаёт и отвечает «устарело» —
    // а это весь поиск, заведение кандидата и привязка ссылки разом.
    const asked = fake({ 'search.local': { ok: [] }, 'search.external': { ok: [] } })

    await numbered('search.local', 'movie', 'один', { channel: 'search' })
    await numbered('search.external', { channel: 'search', op: lastOp('search') })

    expect(asked[1][1][0]).toBe(asked[0][1][0])
  })

  it('номер ложится в список отменяемых', async () => {
    // Иначе `cancel` зовётся с пустотой всегда, и обещание «страница ушла —
    // начатое отменяется» не наступает нигде.
    const ops = []
    fake({ 'world.enrich': { ok: [] } })

    await numbered('world.enrich', 12, 'movie', { ops })

    expect(ops).toHaveLength(1)
    expect(typeof ops[0]).toBe('number')
  })

  it('устаревший ответ не затирает свежий', async () => {
    // Набрал новый запрос, пока летел старый. Обещание старого обязано
    // отклониться, а не вернуть данные, которых уже никто не ждёт.
    const slow = new Promise((resolve) => setTimeout(() => resolve({ ok: 'старое' }), 20))
    let first = true
    fake({
      'search.local': () => {
        if (first) { first = false; return slow }
        return { ok: 'новое' }
      },
    })

    const stale = numbered('search.local', 'movie', 'один', { channel: 'search' })
    const fresh = await numbered('search.local', 'movie', 'два', { channel: 'search' })

    expect(fresh).toBe('новое')
    await expect(stale).rejects.toThrow(Failed)
  })

  it('ответы разных каналов друг друга не гасят', async () => {
    // Лента и поиск идут разом, и номер у них общий: без канала свежая
    // страница ленты отменяла бы свежую выдачу поиска.
    fake({ 'search.local': { ok: 'своё' }, 'feed.page': { ok: [] } })

    const feed = numbered('feed.page', {}, 0, 50, { channel: 'feed' })
    const search = numbered('search.local', 'movie', 'один', { channel: 'search' })

    await expect(feed).resolves.toEqual([])
    await expect(search).resolves.toBe('своё')
  })

  it('отмена уходит одним пересечением границы', async () => {
    // Страница ушла целиком: восемнадцать вызовов вместо одного — это
    // восемнадцать потоков на стороне питона.
    const asked = fake({})

    cancel([1, 2, 3])

    expect(asked[0]).toEqual(['cancel', [1, 2, 3]])
  })

  it('отменённая операция молчит, а не поднимает плашку', async () => {
    fake({ 'world.enrich': { fail: 'cancelled' } })

    await expect(numbered('world.enrich', 12, 'movie')).rejects.toThrow(Failed)
    await numbered('world.enrich', 12, 'movie').catch((error) => {
      expect(error.silent).toBe(true)
    })
  })

  it('ждёт готовности моста, а не падает на его отсутствии', async () => {
    // Инъекция идёт после навигации, и обращение до неё нашло бы undefined.
    const listeners = {}
    globalThis.window = {
      addEventListener: (name, handler) => { listeners[name] = handler },
    }

    const waiting = ready()
    globalThis.window.pywebview = { api: {} }
    listeners.pywebviewready()

    await expect(waiting).resolves.toBeUndefined()
  })
})
```

- [ ] **Шаг 2: Прогнать и увидеть красное**

```bash
cd client && npm test
```

Ожидание: FAIL, `Cannot find module '$api/bridge.js'`.

- [ ] **Шаг 3: Написать обёртку**

Создать `client/api/bridge.js`:

```js
/** Единственное место страницы, которое знает про `window.pywebview`. */

/** Отказ операции: род один на все семь исключений бэкенда. */
export class Failed extends Error {
  constructor(kind, detail = '') {
    super(detail || kind)
    this.name = 'Failed'
    this.kind = kind
    this.detail = detail
    // Отменённое и устаревшее плашкой не показываются: за уход со страницы
    // человеку сообщать не о чем.
    this.silent = kind === 'cancelled' || kind === 'stale'
  }
}

let counter = 0

// Последний номер на канал. Канал — это то, что вытесняет само себя: новая
// выдача поиска отменяет прежнюю, но не отменяет страницу ленты.
const latest = new Map()

/** Инъекция моста идёт после навигации: до неё `window.pywebview` не существует. */
export function ready() {
  if (window.pywebview) return Promise.resolve()
  return new Promise((resolve) => {
    window.addEventListener('pywebviewready', () => resolve())
  })
}

/** Вызов без номера: мгновенные операции, которые нечем отменять. */
export async function call(path, ...args) {
  await ready()
  return unwrap(await at(path)(...args))
}

/**
 * Вызов с номером: его есть чем отменить, и его ответ может устареть.
 *
 * Номер уходит наружу двумя путями, и оба обязательны. `options.op` — чужой
 * номер: второй шаг двухшаговой операции обязан прийти с тем же, что и первый,
 * иначе мостовая память его не узнает и ответит «устарело», а это весь поиск,
 * заведение кандидата и привязка ссылки разом. `options.ops` — список, куда
 * номер кладётся: без него уход с раздела гасить нечего, и `cancel` зовётся с
 * пустотой всегда.
 */
export async function numbered(path, ...args) {
  const options = tail(args)
  const channel = options.channel ?? path
  const op = options.op ?? (counter += 1)
  latest.set(channel, op)
  options.ops?.push(op)

  await ready()
  const answer = await at(path)(op, ...args)

  // Номер читается в момент доставки, а не отправки: пока летел ответ,
  // страница могла спросить заново.
  if (latest.get(channel) !== op) throw new Failed('stale')
  return unwrap(answer)
}

/** Номер последней операции канала — им зовётся второй шаг. */
export function lastOp(channel) {
  return latest.get(channel)
}

/** Страница ушла — гасим всё, что начала, одним пересечением границы. */
export function cancel(ops) {
  // Мост проверяется, а не предполагается: уход с раздела бывает и до инъекции,
  // и после закрытия окна, а `ready()` тут ждать нечего — гасить уже нечего.
  if (ops.length && window.pywebview) window.pywebview.api.cancel(ops)
}

function at(path) {
  const [domain, method] = path.split('.')
  return (...args) => window.pywebview.api[domain][method](...args)
}

function unwrap(answer) {
  if ('ok' in answer) return answer.ok
  throw new Failed(answer.fail, answer.detail)
}

const OPTIONS = ['channel', 'op', 'ops']

/** Последний довод — настройки вызова, а не часть запроса. */
function tail(args) {
  const last = args.at(-1)
  if (last && typeof last === 'object' && OPTIONS.some((one) => one in last)) {
    args.pop()
    return last
  }
  return {}
}
```

- [ ] **Шаг 4: Прогнать и увидеть зелёное**

```bash
cd client && npm test
```

Ожидание: PASS, 43 теста — одиннадцать новых и тридцать два из задачи 3.

- [ ] **Шаг 5: Коммит**

```bash
git add client/api/ tests/web/bridge.test.js
git commit -m "feat: обёртка моста — номер, отмена, устаревший ответ"
```

---

### Задача 5: Шапка

Блок макета целиком: три зоны, поиск с очисткой, переключатель типа с
перекраской акцента, ряд из девяти круглых кнопок четырёх поведений.

**Проверяется запуском, а не тестом.** Компоненты по решению не проверяются, и
единственная проверка здесь — открыть окно и посмотреть. Смотреть надо на
собранную шапку, а не на её треть, поэтому она и делается одной задачей.

**Ширина зон считается замером, а не числом в CSS.** Боковые зоны равны ширине
переключателя, а её задаёт самая длинная подпись — то есть шрифт. Пересчёт идёт
по `document.fonts.ready` и по изменению размеров: шрифт приезжает позже
разметки, и первый замер без него врёт.

**Акцент закреплён за типом содержимого.** Фильмам достаётся объявленный в
палитре, поэтому в таблице только два, что его перебивают: иначе одно и то же
значение лежало бы в двух местах и могло разойтись.

**Файлы:**
- Создать: `client/components/Icon.svelte`, `SearchField.svelte`,
  `Segmented.svelte`, `ToolButton.svelte`
- Создать: `client/styles/topbar.css`, `search.css`, `seg.css`,
  `tools.css`
- Создать: `client/app/Topbar.svelte`
- Изменить: `client/app/App.svelte`, `client/main.js`

**Интерфейсы:**
- Потребляет: `nextSort`, `stateAt` из `$state/sorting.js`; `isEmpty` из
  `$state/filters.js`; `withKind`, `withSection`, `withCollapsed` из
  `$state/session.js`.
- Отдаёт: `Topbar` с входными `session`, `onsession`, `onsearch`, `onadd`,
  `onfilter`.

- [ ] **Шаг 1: Перенести стили шапки**

Четыре файла, значения из `docs/design/index.html:78-326` точь-в-точь.

`client/styles/topbar.css`:

```css
/* Три зоны: переключатель держится центра окна независимо от того, насколько
   длинное имя справа. */
.topbar {
  /* Все три блока одной ширины — по переключателю. Значение ставит замер;
     здесь запас до первого срабатывания. */
  --side-w: 370px;
  --corner: 24px;

  flex: 0 0 auto;
  display: grid;
  grid-template-columns: auto auto auto;
  justify-content: center;
  align-items: center;
  column-gap: 18px;
  padding: 14px var(--corner);
}

.content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
```

`client/styles/search.css`:

```css
.search {
  grid-column: 1;
  width: var(--side-w);
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;                /* вровень с капсулой переключателя */
  padding: 0 16px;
  border-radius: var(--r-full);
  background: var(--tint-035);
  border: 1px solid var(--tint-06);
  transition: background .18s, border-color .18s;
}

.search:hover {
  background: var(--tint-05);
  border-color: var(--tint-10);
}

.search:focus-within {
  background: var(--tint-05);
  border-color: color-mix(in srgb, var(--primary) 45%, transparent);
}

.search__icon {
  flex: 0 0 auto;
  font-size: 20px;
  color: var(--tint-35);
  transition: color .18s;
}
.search:focus-within .search__icon { color: var(--primary) }

.search__input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text);
  font: var(--body-l);
  caret-color: var(--primary);
  user-select: text;
}
.search__input::placeholder { color: var(--tint-28) }

/* Своя кнопка очистки вместо системной: та рисуется цветом ОС. */
.search__input::-webkit-search-cancel-button,
.search__input::-webkit-search-decoration {
  appearance: none;
}

.search__clear {
  flex: 0 0 auto;
  display: block;
  width: 26px;
  height: 26px;
  margin-right: -6px;
  padding: 0;
  border: none;
  border-radius: var(--r-full);
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  transition: background .15s;
}

/* Центрируем межстрочным интервалом: у иконочного шрифта глиф сидит на базовой
   линии, и выравнивание по коробке уводит его вниз. */
.search__clear .material-symbols-outlined {
  display: block;
  width: 26px;
  font-size: 18px;
  line-height: 26px;
  text-align: center;
}
.search__clear:hover {
  background: color-mix(in srgb, var(--primary) 14%, transparent);
}
```

`client/styles/seg.css`:

```css
/* Колонки в 1fr при авто-ширине контейнера выравниваются по самой широкой —
   сегменты получаются одинаковыми без ручной ширины. */
.seg {
  grid-column: 2;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 2px;
  padding: 3px;
  border-radius: var(--r-full);
  background: var(--tint-035);
  border: 1px solid var(--tint-06);
}

.seg__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 7px 16px;
  white-space: nowrap;
  border: none;
  border-radius: var(--r-full);
  background: transparent;
  color: var(--tint-45);
  font: var(--title-s);
  cursor: pointer;
  transition: background .18s, color .18s;
}
.seg__btn .material-symbols-outlined { font-size: 19px }

.seg__btn:hover {
  background: var(--tint-05);
  color: var(--tint-75);
}

.seg__btn.is-active {
  background: color-mix(in srgb, var(--primary) 14%, transparent);
  color: var(--primary);
}
.seg__btn.is-active:hover {
  background: color-mix(in srgb, var(--primary) 20%, transparent);
}
```

`client/styles/tools.css`:

```css
/* Подложка та же, что у переключателя; кнопка 34px плюс отступы даёт ровно те
   же 42px высоты. */
.tools {
  grid-column: 3;
  width: var(--side-w);
  display: flex;
  justify-content: space-between;
  padding: 3px;
  border-radius: var(--r-full);
  background: var(--tint-035);
  border: 1px solid var(--tint-06);
}

.tools__btn {
  position: relative;
  flex: 0 0 auto;             /* иконки не должны сплющиваться в овалы */
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: var(--r-full);
  background: transparent;
  color: var(--tint-45);
  cursor: pointer;
  transition: background .18s, color .18s;
}
.tools__btn .material-symbols-outlined { font-size: 19px }

.tools__btn:hover {
  background: var(--tint-05);
  color: var(--tint-75);
}

.tools__btn.is-active {
  background: color-mix(in srgb, var(--primary) 14%, transparent);
  color: var(--primary);
}

/* Сортировка: критерий крупной иконкой, направление — стрелкой в углу.
   Критерий сдвинут, чтобы стрелка не наезжала на него. */
.tools__btn[data-role="sort"] .material-symbols-outlined {
  transform: translate(-3px,-2px);
}
.tools__dir {
  position: absolute;
  right: 1px;
  bottom: 1px;
  font-size: 13px !important;
  transform: none !important;
}

/* Гистограмма — не шрифтовой глиф, а SVG: столбики должны расти поодиночке, а
   у иконки шрифта частей нет. */
.tools__chart {
  width: 19px;
  height: 19px;
  display: block;
  fill: currentColor;
}
.tools__chart rect {
  transform-box: fill-box;
  transform-origin: 50% 100%;   /* растём от пола, а не от центра */
}

/* Класс вешается на каждый щелчок, а не держится состоянием — иначе анимация
   играла бы только при включении. */
.is-drawing .tools__chart rect {
  animation: bar-grow .42s cubic-bezier(.2,.8,.2,1) both;
}
.is-drawing .tools__chart rect:nth-child(2) { animation-delay: .07s }
.is-drawing .tools__chart rect:nth-child(3) { animation-delay: .14s }

@keyframes bar-grow {
  from { transform: scaleY(0) }
  to   { transform: scaleY(1) }
}
```

- [ ] **Шаг 2: Написать компоненты**

`client/components/Icon.svelte`:

```svelte
<script>
  let { name, extra = '' } = $props()
</script>

<span class="material-symbols-outlined {extra}" aria-hidden="true">{name}</span>
```

`client/components/SearchField.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  let { value = '', onsearch } = $props()

  let field
  // Очистка возвращает фокус в поле: убрал текст — печатай дальше, а не ищи
  // курсор мышью.
  const clear = () => { value = ''; field.focus() }
</script>

<label class="search">
  <Icon name="search" extra="search__icon" />
  <input class="search__input" type="search" placeholder="Поиск" aria-label="Поиск"
         spellcheck="false" autocomplete="off"
         bind:this={field} bind:value
         onkeydown={(event) => event.key === 'Enter' && onsearch(value.trim())}>
  {#if value}
    <button type="button" class="search__clear" aria-label="Очистить" onclick={clear}>
      <Icon name="close" />
    </button>
  {/if}
</label>
```

Поиск идёт по Enter, а не на каждую букву: одна буква — это запрос к внешней
базе, а их квоты конечны.

`client/components/Segmented.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  let { items, chosen, onchoose } = $props()
</script>

<nav class="seg">
  {#each items as item (item.value)}
    <button type="button" class="seg__btn" class:is-active={item.value === chosen}
            aria-pressed={item.value === chosen}
            onclick={() => onchoose(item.value)}>
      <Icon name={item.icon} />
      <span class="seg__label">{item.label}</span>
    </button>
  {/each}
</nav>
```

`client/components/ToolButton.svelte`:

```svelte
<script>
  import Icon from '$components/Icon.svelte'

  let { icon, dir = '', label, active = false, pressed = null, onclick,
        children } = $props()
</script>

<button type="button" class="tools__btn" class:is-active={active}
        aria-pressed={pressed} aria-label={label} title={label} {onclick}>
  {#if children}{@render children()}{:else}
    <Icon name={icon} />
    {#if dir}<Icon name={dir} extra="tools__dir" />{/if}
  {/if}
</button>
```

`children` нужен одной кнопке из девяти — статистике: её иконка не глиф, а SVG
из трёх столбиков, потому что они растут поодиночке.

- [ ] **Шаг 3: Собрать шапку**

Создать `client/app/Topbar.svelte`:

```svelte
<script>
  import SearchField from '$components/SearchField.svelte'
  import Segmented from '$components/Segmented.svelte'
  import ToolButton from '$components/ToolButton.svelte'
  import { isEmpty } from '$state/filters.js'
  import { withCollapsed, withKind, withSection } from '$state/session.js'
  import { nextSort, stateAt } from '$state/sorting.js'

  let { session, onsession, onsearch, onadd, onfilter } = $props()

  const KINDS = [
    { value: 'movie',  icon: 'movie',           label: 'Фильмы' },
    { value: 'series', icon: 'live_tv',         label: 'Сериалы' },
    { value: 'game',   icon: 'sports_esports',  label: 'Игры' },
  ]

  // Фильмам достаётся значение по умолчанию из палитры, поэтому его тут нет:
  // положить одно значение в два места значит дать ему разойтись. Остальные два
  // подставляются токенами, а не литералами — цвет живёт в палитре.
  const ACCENTS = { series: 'var(--accent-series)', game: 'var(--accent-game)' }

  const VIEWS = [
    { value: 'rated',    icon: 'thumb_up', label: 'Оценённые' },
    { value: 'wishlist', icon: 'bookmark', label: 'Хочу посмотреть' },
  ]

  const FILTERS = [
    { field: 'genres', icon: 'category', label: 'Жанры' },
    { field: 'tags',   icon: 'label',    label: 'Теги' },
    { field: 'scores', icon: 'star',     label: 'Фильтр по оценке' },
  ]

  let drawing = $state(false)

  // Вид кнопки — из состояния своего раздела: позиция 0 в отложенном и в
  // оценённых означает разное.
  const sort = $derived(stateAt(session.section, session.sort ?? 0))

  function chooseKind(kind) {
    const root = document.documentElement.style
    const accent = ACCENTS[kind]
    accent ? root.setProperty('--primary', accent) : root.removeProperty('--primary')
    onsession(withKind(session, kind))
  }

  // Повторный щелчок по разделу возвращает простой список: раздел — это
  // подмена содержимого, а не переключатель с залипанием.
  const chooseView = (value) =>
    onsession(withSection(session, session.section === value ? 'search' : value))

  function chooseStats() {
    // Класс вешается на каждый заход, а не держится состоянием: иначе
    // столбики иконки отрастут один раз за всё время работы.
    drawing = false
    requestAnimationFrame(() => { drawing = true })
    chooseView('stats')
  }
</script>

<header class="topbar">
  <SearchField {onsearch} />

  <Segmented items={KINDS} chosen={session.kind} onchoose={chooseKind} />

  <div class="tools" class:is-drawing={drawing}>
    {#each VIEWS as view (view.value)}
      <ToolButton icon={view.icon} label={view.label}
                  active={session.section === view.value}
                  pressed={session.section === view.value}
                  onclick={() => chooseView(view.value)} />
    {/each}

    <ToolButton label="Статистика" active={session.section === 'stats'}
                pressed={session.section === 'stats'} onclick={chooseStats}>
      {#snippet children()}
        <svg class="tools__chart" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="4"  y="9"  width="4" height="11" />
          <rect x="10" y="4"  width="4" height="16" />
          <rect x="16" y="13" width="4" height="7" />
        </svg>
      {/snippet}
    </ToolButton>

    {#each FILTERS as filter (filter.field)}
      <ToolButton icon={filter.icon} label={filter.label}
                  active={!isEmpty(session.filters)}
                  pressed={!isEmpty(session.filters)}
                  onclick={() => onfilter(filter.field)} />
    {/each}

    <ToolButton icon={session.collapsed ? 'unfold_more' : 'unfold_less'}
                label={session.collapsed ? 'Развернуть всё' : 'Свернуть всё'}
                active={session.collapsed} pressed={session.collapsed}
                onclick={() => onsession(withCollapsed(session, !session.collapsed))} />

    <ToolButton icon={sort.icon} dir={sort.dir}
                label={'Сортировка: ' + sort.label.toLowerCase()}
                onclick={() => onsession({
                  ...session,
                  sort: nextSort(session.section, session.sort ?? 0),
                })} />

    <ToolButton icon="add" label="Завести карточку" onclick={onadd} />
  </div>
</header>
```

**Кнопка фильтра горит, пока фильтр задан, а не пока открыта модалка** — и это
общее состояние на три кнопки: спека говорит «горят пока фильтр применён», а
применён он один на все признаки. Разбор по признакам появится в плане 8, вместе
с самими модалками.

**Набор состояний сортировки зависит от раздела.** Решено 31.07.2026: в
«Оценённых» их восемь, в «Хочу посмотреть» четыре — по дате добавления и по
алфавиту, каждый в две стороны. Кнопка одна и та же, но перебирает она свой
набор, и вид берёт из него же.

- [ ] **Шаг 4: Считать ширину зон замером**

Дописать в `client/app/App.svelte` — измеряется переключатель, а не
задаётся числом: его ширину определяет самая длинная подпись, то есть шрифт.

```svelte
<script>
  import Topbar from './Topbar.svelte'
  import { newSession } from '$state/session.js'

  let session = $state(newSession())
  let topbar = $state()

  // Шрифт приезжает позже разметки, и первый замер без него врёт: подписи
  // ещё системные, ширина другая.
  $effect(() => {
    const measure = () => {
      const seg = topbar?.querySelector('.seg')
      const bar = topbar?.querySelector('.topbar')
      if (!seg || !bar) return
      bar.style.setProperty('--side-w', `${Math.ceil(seg.offsetWidth)}px`)
    }

    document.fonts.ready.then(measure)
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  })
</script>

<div class="app">
  <main class="app__main" bind:this={topbar}>
    <Topbar {session}
            onsession={(next) => { session = next }}
            onsearch={() => {}} onadd={() => {}} onfilter={() => {}} />
    <div class="content"></div>
  </main>
</div>
```

`--content-w` здесь не считается: её потребители — гистограмма и лента, и
появятся они в планах 7 и 8. Заводить её раньше значило бы завести переменную
без сегодняшнего потребителя.

- [ ] **Шаг 5: Подключить стили**

Дописать в `client/main.js` после базовых:

```js
import '$styles/topbar.css'
import '$styles/search.css'
import '$styles/seg.css'
import '$styles/tools.css'
```

- [ ] **Шаг 6: Собрать и посмотреть**

```bash
cd client && npm run build
cd ../.. && pipenv run python main.py
```

Сверить с макетом (`docs/design/index.html` открыть в браузере рядом):

- три зоны, переключатель ровно по центру окна;
- поиск и ряд кнопок одной ширины с переключателем;
- крестик очистки появляется, только когда в поле что-то есть;
- переключение типа перекрашивает акцент **перетеканием**, а не скачком:
  салатовый → синий → жёлтый;
- включённая кнопка показывает закрашенную иконку, выключенная — контурную;
- щелчок по сортировке меняет и глиф, и стрелку, по кругу из восьми;
- заход на статистику отращивает три столбика иконки.

- [ ] **Шаг 7: Коммит**

```bash
git add client/components/ client/styles/ \
        client/app/ client/main.js
git commit -m "feat: шапка целиком — поиск, переключатель типа, девять кнопок"
```

---

### Задача 6: Стопка разделов и плашка

Последний блок каркаса: четыре раздела, лежащие стопкой, переход между ними
проявлением и единственное место, где приложение что-либо сообщает.

**Переходы нативные, а не браузерная навигация.** Страницы лежат в стопке,
старая исчезает сразу, новая проявляется из прозрачности за 0.16 с. Причина не
только в виде: корень `/` у сервера pywebview отвечает `500`, и любая
перезагрузка страницы сломала бы приложение — маршрутизации по адресу тут нет
вовсе.

**Плашка одна на всё приложение.** Ни надписей поверх ленты, ни пометок внутри
выдачи, ни отдельных экранов под случай. Пустая выдача — не событие: плашка
появляется, только когда база **не ответила**.

**Файлы:**
- Создать: `client/styles/view.css`, `snack.css`
- Создать: `client/components/Snack.svelte`
- Создать: `client/app/SearchScreen.svelte`, `LibraryScreen.svelte`,
  `StatsScreen.svelte`
- Изменить: `client/app/App.svelte`, `client/main.js`

**Интерфейсы:**
- Потребляет: `session` из задачи 3, `Failed` из `$api/bridge.js`.
- Отдаёт: `Snack` с входными `text`; четыре экрана без входных параметров —
  наполняются планами 7–9.

- [ ] **Шаг 1: Перенести стили**

`client/styles/view.css`:

```css
.view { display: none }

/* Высота именно задана, а не минимальна: содержимое считает свои проценты
   от неё. */
.view.is-shown {
  display: flex;
  flex-direction: column;
  height: 100%;
  animation: screen-in .16s ease-out;
}

@keyframes screen-in {
  from { opacity: 0 }
  to   { opacity: 1 }
}
```

`client/styles/snack.css`:

```css
/* Единственное место, где приложение что-то сообщает: и отказ источника, и
   непредвиденный сбой. Уехавшая вниз плашка пустая — отсутствие сообщений само
   себя ничем не обозначает. */
.snack {
  --neon: var(--error);
  --halo-h: 30px;

  position: fixed;
  left: 50%;
  bottom: 24px;
  z-index: 20;
  max-width: min(560px, calc(100vw - 48px));
  padding: 12px 24px;
  border-radius: var(--r-full);
  font: var(--body-m);
  text-align: center;

  background: var(--glass-error);
  backdrop-filter: blur(14px) saturate(125%);

  transform: translate(-50%, calc(100% + 32px));
  transition: transform .22s cubic-bezier(.2,.8,.2,1);
}

.snack.is-shown { transform: translate(-50%, 0) }
```

- [ ] **Шаг 2: Написать плашку**

Создать `client/components/Snack.svelte`:

```svelte
<script>
  // Сколько держится сообщение. Значение из макета: плашка выезжает, держится
  // несколько секунд и уходит.
  const LINGER = 4000

  let { text = '' } = $props()

  let shown = $state(false)
  let last = $state('')

  // Второе сообщение заменяет первое и заводит отсчёт заново, а не встаёт в
  // очередь: свежая беда важнее прошлой.
  $effect(() => {
    if (!text) return
    last = text
    shown = true
    const timer = setTimeout(() => { shown = false }, LINGER)
    return () => clearTimeout(timer)
  })
</script>

<div class="snack neon" class:is-shown={shown} role="status" aria-live="polite">
  {last}
</div>
```

Текст остаётся в `last` после ухода плашки нарочно: пустая строка в момент
отъезда стёрла бы надпись на середине движения.

- [ ] **Шаг 3: Написать четыре экрана**

Все четыре пока пусты — их наполняют планы 7–9. Заводятся сейчас потому, что
стопка и переход между разделами проверяются только на настоящих разделах.

`client/app/SearchScreen.svelte`:

```svelte
<div class="feed"></div>
```

`LibraryScreen.svelte` — то же самое.
`StatsScreen.svelte`:

```svelte
<div class="chart"></div>
```

- [ ] **Шаг 4: Собрать стопку**

Дописать `client/app/App.svelte`: раздел выбирается один, остальные не
рисуются вовсе.

```svelte
<script>
  import LibraryScreen from './LibraryScreen.svelte'
  import SearchScreen from './SearchScreen.svelte'
  import StatsScreen from './StatsScreen.svelte'
  import Topbar from './Topbar.svelte'
  import Snack from '$components/Snack.svelte'
  import { newSession } from '$state/session.js'

  const SCREENS = {
    search: SearchScreen,
    // Оба раздела библиотеки — один экран: различает их `session.section`,
    // и он же уезжает в запрос. Второй файл был бы копией на шестьдесят пять
    // строк, которую планы 8 и 9 правили бы дважды.
    rated: LibraryScreen,
    wishlist: LibraryScreen,
    stats: StatsScreen,
  }

  let session = $state(newSession())
  let trouble = $state('')
  let topbar = $state()

  const Screen = $derived(SCREENS[session.section])

  $effect(() => {
    const measure = () => {
      const seg = topbar?.querySelector('.seg')
      const bar = topbar?.querySelector('.topbar')
      if (!seg || !bar) return
      bar.style.setProperty('--side-w', `${Math.ceil(seg.offsetWidth)}px`)
    }

    document.fonts.ready.then(measure)
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  })
</script>

<div class="app">
  <main class="app__main" bind:this={topbar}>
    <Topbar {session}
            onsession={(next) => { session = next }}
            onsearch={() => {}} onadd={() => {}} onfilter={() => {}} />

    <div class="content">
      {#key session.section}
        <section class="view is-shown">
          <Screen />
        </section>
      {/key}
    </div>
  </main>

  <Snack text={trouble} />
</div>
```

`{#key}` здесь не украшение: без него Svelte переиспользует ту же секцию, и
`screen-in` не проигрывается — переход между разделами станет мгновенной
подменой.

- [ ] **Шаг 5: Подключить стили**

Дописать в `client/main.js`:

```js
import '$styles/view.css'
import '$styles/snack.css'
```

- [ ] **Шаг 6: Собрать и посмотреть**

```bash
cd client && npm run build
cd ../.. && pipenv run python main.py
```

Ожидание:

- переключение между разделами идёт проявлением, а не рывком;
- повторный щелчок по включённому разделу возвращает поиск;
- плашка не видна: сообщать пока не о чем, и отсутствие сообщений само себя
  ничем не обозначает.

**Проверить плашку живьём:** временно поставить `let trouble = $state('Внешняя
база недоступна')` — плашка обязана выехать снизу, продержаться и уехать. После
проверки вернуть пустую строку.

- [ ] **Шаг 7: Записать вторую цепочку выпуска**

В `CLAUDE.md`, раздел «Окружение», дописать команды фронта рядом с питоновскими:
сборка `npm run build` из `client`, прогон `npm test`. Без этого из чистого
клона рабочую страницу соберёт только тот, кто уже собирал.

- [ ] **Шаг 8: Коммит**

```bash
git add client/ CLAUDE.md
git commit -m "feat: четыре раздела стопкой, переход проявлением, плашка"
```

---

## Самопроверка плана

**Покрытие.** Спека клиента, раздел «Состояние приложения» — задача 3 целиком
(тип, свёрнутость, фильтры, сортировка, номер запроса поиска живёт в обёртке
моста). Раздел «Мост», страничная половина — задача 4. Спека разделов, «Один
переключатель, восемь состояний» и «Три состояния строки фильтра» — задачи 3 и 5.
`errors.md`, «Одна плашка на все сообщения» — задача 6.

**Что этот план сознательно не делает.** Ни одной карточки: лента пуста, и
`.feed` — пустой блок. Модалок нет вовсе, и кнопки фильтров зовут пустой
обработчик. Гистограммы нет. `--content-w` не считается: её потребители
появятся в планах 7 и 8, и раньше это была бы переменная без потребителя.
Разбор «какой именно фильтр применён» по признакам — план 8: сейчас все три
кнопки горят от одного `isEmpty`, как и написано в спеке.

**Чем измеряется готовность.** `npm test` зелёный, 41 тест. Окно открывается,
шапка совпадает с макетом при сверке рядом, переключение типа перетекает
акцентом, разделы меняются проявлением, плашка выезжает и уходит.
