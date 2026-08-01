/* Доля каждого столбца от самого высокого. */

/** Столбцы показывают соотношение, а не вклад в целое: от суммы самый высокий
 *  занял бы доли процента, и гистограмма выглядела бы плоской на любой
 *  библиотеке. */
export function heightsOf(buckets) {
  const peak = Math.max(...buckets.map((one) => one.count), 0)
  return buckets.map((one) => (peak ? one.count / peak : 0))
}
