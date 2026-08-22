import '@fontsource-variable/roboto'
import 'material-symbols/outlined.css'
import { mount } from 'svelte'

import App from './app/App.svelte'
import { call } from '$api/bridge.js'
import { setScale } from '$state/scores.js'
// Палитра первой: без неё база возьмёт неопределённые переменные.
import '$styles/palette.css'
import '$styles/base.css'
import '$styles/neon.css'
import '$styles/iconbutton.css'
import '$styles/app.css'
import '$styles/topbar.css'
import '$styles/zone.css'
import '$styles/field.css'
import '$styles/search.css'
import '$styles/seg.css'
import '$styles/tools.css'
import '$styles/view.css'
import '$styles/snack.css'
import '$styles/feed.css'
import '$styles/film.css'
import '$styles/chips.css'
import '$styles/facts.css'
import '$styles/stars.css'
import '$styles/aggr.css'
import '$styles/acts.css'
import '$styles/chart.css'
import '$styles/modal.css'
import '$styles/modalfoot.css'
import '$styles/scrollarea.css'
import '$styles/review.css'
import '$styles/taglist.css'
import '$styles/scorerow.css'
import '$styles/addline.css'
import '$styles/chosen.css'
import '$styles/cardform.css'
import '$styles/picker.css'

// Сколько ждём мост, прежде чем рисовать на десяти ступенях. Срок обязателен:
// `ready()` ждёт внедрения моста событием и отклоняться не умеет вовсе, а в
// `npm run dev` окна нет — без срока страница не смонтировалась бы никогда, и
// правка разметки шла бы по пустому экрану.
const SCALE_WAIT = 2000

// Ступени спрашиваются до отрисовки, а не в эффекте: приехав после первого
// кадра, они сменили бы десять звёзд на пять у человека на глазах.
//
// Ни отказ, ни молчание окну открыться не мешают — шкала остаётся
// десятибалльной, — но молчать о них нельзя: ярлыки, цвета и столбцы
// разошлись бы с базой, и понять почему было бы нечем.
const waited = new Promise((resolve) => { setTimeout(resolve, SCALE_WAIT) })
try {
  const steps = await Promise.race([call('refs.scale'), waited])
  if (steps) setScale(steps)
  else console.error('шкала не приехала за срок, остаёмся на десяти ступенях')
} catch (error) {
  console.error('шкала не приехала, остаёмся на десяти ступенях', error)
}

export default mount(App, { target: document.getElementById('root') })
