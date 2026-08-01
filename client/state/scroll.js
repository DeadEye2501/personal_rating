/* Арифметика своей полосы прокрутки. */

// Минимальная высота ползунка: на длинном списке доля содержимого делает его
// неухватываемым.
const MIN_THUMB = 28

// Высоты браузер отдаёт целыми, и разница в пиксель бывает округлением, а не
// содержимым.
const NOISE = 1

/** Ползунок целиком, либо `null` — прокручивать нечего.
 *
 *  `scale` считается по дорожке самого ползунка, а не долей видимого от всего:
 *  доля верна, только пока высота не подпёрта снизу. Подпёртый ползунок,
 *  доведённый до низа дорожки, при доле не довёл бы список до конца. */
export function thumbOf(visible, total, passed) {
  if (total <= visible + NOISE) return null

  const height = Math.max(MIN_THUMB, visible * (visible / total))
  const room = visible - height
  const range = total - visible
  return { height, offset: room * (passed / range), scale: range / room }
}
