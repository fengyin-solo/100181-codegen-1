<template>
  <div class="limit-editor">
    <p class="form-tip">
      每侧可留空表示不设该方向限值；同一指标需满足
      合格下限 ≤ 预警下限 ≤ 预警上限 ≤ 合格上限。
    </p>
    <table class="limit-grid">
      <thead>
        <tr>
          <th>指标</th>
          <th v-for="key in keys" :key="key">{{ labels[key] }}</th>
          <th>单位</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="metric in metrics" :key="metric">
          <td class="metric-name">{{ metric }}</td>
          <td v-for="key in keys" :key="key">
            <input
              v-model="draft[metric][key]"
              type="number"
              step="0.01"
              :placeholder="metric === '浊度' && key.includes('min') ? '不限' : '数值'"
            />
          </td>
          <td class="metric-unit">{{ units[metric] || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <label class="form-row" v-if="showRemark">
      <span>调整说明</span>
      <input v-model="remarkValue" placeholder="例如：浊度限值由 1.0 收紧至 0.8" />
    </label>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import type { Bound, LimitsDoc } from '@/api/water'
import { LIMIT_KEYS, LIMIT_LABELS, METRICS, METRIC_UNITS } from '@/api/water'

type CellValue = number | string | null
type DraftDoc = Record<string, Record<string, CellValue>>

const props = defineProps<{
  modelValue: LimitsDoc
  showRemark?: boolean
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: LimitsDoc): void
  (e: 'update:remark', value: string): void
}>()

const keys = [...LIMIT_KEYS]
const metrics = [...METRICS]
const units = METRIC_UNITS
const labels = LIMIT_LABELS

function toDraft(source: LimitsDoc): DraftDoc {
  const result: DraftDoc = {}
  for (const metric of metrics) {
    result[metric] = {}
    for (const key of keys) {
      result[metric][key] = source[metric]?.[key] ?? null
    }
  }
  return result
}

const draft = reactive<DraftDoc>(toDraft(props.modelValue))
const remarkValue = ref(props.showRemark ? '' : '')

watch(
  draft,
  () => emit('update:modelValue', normalized()),
  { deep: true },
)
watch(remarkValue, (value) => emit('update:remark', value))

/** input 清空后是空串，提交前统一转成 null。 */
function normalized(): LimitsDoc {
  const result: LimitsDoc = {}
  for (const metric of metrics) {
    const bound = {} as Bound
    for (const key of keys) {
      const raw = draft[metric][key]
      const num = raw === '' || raw === null ? NaN : Number(raw)
      bound[key] = Number.isFinite(num) ? num : null
    }
    result[metric] = bound
  }
  return result
}

defineExpose({ normalized })
</script>
