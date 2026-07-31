import '@fontsource-variable/roboto'
import 'material-symbols/outlined.css'
import { mount } from 'svelte'

import App from './app/App.svelte'
// Палитра первой: без неё база возьмёт неопределённые переменные.
import '$styles/palette.css'
import '$styles/base.css'
import '$styles/neon.css'

export default mount(App, { target: document.getElementById('root') })
