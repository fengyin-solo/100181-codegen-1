/** 水质限值判定：与后端 services/water_rules.py 保持同一份规则，供录入时实时预览。
 *
 * 批次结论取各指标最严重的一档：限外=超标；限内但进入预警带=预警；其余达标。
 */
import type { Bound, LimitsDoc } from '@/api/water'
import { METRICS } from '@/api/water'

export type MetricVerdict = '达标' | '预警' | '超标'

export interface PreviewMetric {
  metric: string
  value: number | null
  verdict: MetricVerdict | null
}

export function evaluateMetric(limit: Bound | undefined, value: number): MetricVerdict {
  if (!limit) return '达标'
  if (
    (limit.min !== null && value < limit.min) ||
    (limit.max !== null && value > limit.max)
  ) {
    return '超标'
  }
  if (
    (limit.warn_min !== null && value < limit.warn_min) ||
    (limit.warn_max !== null && value > limit.warn_max)
  ) {
    return '预警'
  }
  return '达标'
}

const SEVERITY: Record<MetricVerdict, number> = { 达标: 0, 预警: 1, 超标: 2 }

export function previewBatch(
  limits: LimitsDoc | undefined,
  values: Record<string, string>,
): { metrics: PreviewMetric[]; conclusion: MetricVerdict | null; ready: boolean } {
  const metrics: PreviewMetric[] = METRICS.map((metric) => {
    const raw = values[metric]
    const num = raw === '' || raw === undefined ? NaN : Number(raw)
    if (!Number.isFinite(num) || num < 0) {
      return { metric, value: null, verdict: null }
    }
    return { metric, value: num, verdict: evaluateMetric(limits?.[metric], num) }
  })
  const verdicts = metrics.map((item) => item.verdict)
  const ready = verdicts.every((item) => item !== null)
  const conclusion = ready
    ? (metrics.reduce((worst, item) =>
        SEVERITY[item.verdict as MetricVerdict] > SEVERITY[worst]
          ? (item.verdict as MetricVerdict)
          : worst,
        '达标' as MetricVerdict))
    : null
  return { metrics, conclusion, ready }
}
