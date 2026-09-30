<template>
  <ModalShell :title="mode === 'create' ? '登记采样批次' : `改录批次 ${sample?.编号 ?? ''}`" width="600px" @close="$emit('close')">
    <label class="form-row">
      <span>采样点 <b>*</b></span>
      <select v-model="form.采样点ID" :disabled="mode === 'edit'" @change="onPointChange">
        <option :value="null" disabled>请选择采样点</option>
        <optgroup v-for="district in groupedPoints" :key="district.id" :label="district.片区名称">
          <option v-for="point in district.points" :key="point.id" :value="point.id">
            {{ point.采样点编号 }} · {{ point.采样点名称 }}
          </option>
        </optgroup>
      </select>
    </label>
    <p class="form-tip" v-if="currentPoint">
      所属片区现行口径 {{ currentPoint.现行版本 }}：{{ currentPoint.现行口径 }}
      <span v-if="mode === 'edit'">（改录仅影响待判定批次，仍按现行口径重算）</span>
    </p>

    <div class="form-grid">
      <label class="form-row">
        <span>采样时间 <b>*</b></span>
        <input v-model="form.采样时间" type="datetime-local" />
      </label>
      <label class="form-row">
        <span>采样人员 <b>*</b></span>
        <input v-model="form.采样人员" placeholder="检测/采样人员" />
      </label>
    </div>

    <div class="metric-inputs">
      <label class="form-row" v-for="item in preview.metrics" :key="item.metric">
        <span>
          {{ item.metric }}
          <em class="unit">{{ units[item.metric] }}</em>
        </span>
        <input
          v-model="form[item.metric]"
          type="number"
          step="0.01"
          min="0"
          :class="verdictClass(item.verdict)"
          placeholder="录入实测值"
        />
        <small class="verdict" :class="verdictClass(item.verdict)">
          {{ item.verdict ? item.verdict : '待录入' }}
        </small>
      </label>
    </div>

    <div class="preview-line">
      按现行口径实时判定：
      <b :class="verdictClass(preview.conclusion)">{{ preview.conclusion ?? '请录全余氯、浊度、pH' }}</b>
    </div>

    <label class="form-row" v-if="preview.conclusion === '超标'">
      <span class="danger">超标原因 <b>*</b></span>
      <textarea v-model="form.超标原因" rows="2" placeholder="判定为超标，必须写清不少于 5 个字的原因才能保存"></textarea>
    </label>
    <p class="form-tip danger" v-if="preview.conclusion === '超标' && !reasonOk">
      该批采样按现行口径判定为超标，写清不少于 5 个字的原因后才能保存。
    </p>
    <p class="form-tip" v-else-if="mode === 'create'">
      保存后批次为「待判定」，结论随片区现行口径实时重算；在台账里「出具结论」后按当时那一版锁定留档。
    </p>

    <p v-if="error" class="error-text">{{ error }}</p>

    <template #footer>
      <button class="btn ghost" type="button" @click="$emit('close')">取消</button>
      <button class="btn primary" type="button" :disabled="busy" @click="submit">
        {{ mode === 'create' ? '保存批次' : '保存改录' }}
      </button>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import {
  createSample,
  METRIC_UNITS,
  updateSample,
  type WaterDistrict,
  type WaterPoint,
  type WaterSample,
} from '@/api/water'
import { previewBatch } from '../evaluate'
import ModalShell from './ModalShell.vue'

type FormState = {
  采样点ID: number | null
  采样时间: string
  采样人员: string
  余氯: string
  浊度: string
  pH: string
  超标原因: string
  [key: string]: string | number | null
}

const props = defineProps<{
  mode: 'create' | 'edit'
  districts: WaterDistrict[]
  points: WaterPoint[]
  sample?: WaterSample | null
}>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', message: string): void
}>()

const units = METRIC_UNITS

const form = reactive<FormState>(
  props.mode === 'edit' && props.sample
    ? {
        采样点ID: props.sample.采样点ID,
        采样时间: props.sample.采样时间.replace(' ', 'T'),
        采样人员: props.sample.采样人员,
        余氯: String(props.sample.readings.余氯 ?? ''),
        浊度: String(props.sample.readings.浊度 ?? ''),
        pH: String(props.sample.readings.pH ?? ''),
        超标原因: props.sample.超标原因 ?? '',
      }
    : {
        采样点ID: null,
        采样时间: '',
        采样人员: '',
        余氯: '',
        浊度: '',
        pH: '',
        超标原因: '',
      },
)

const groupedPoints = computed(() =>
  props.districts
    .map((district) => ({
      ...district,
      points: props.points.filter(
        (point) => point.片区ID === district.id && point.启用,
      ),
    }))
    .filter((district) => district.points.length),
)

const currentPoint = computed(() =>
  props.points.find((point) => point.id === form.采样点ID) ?? null,
)
const currentDistrict = computed(() =>
  props.districts.find((district) => district.id === currentPoint.value?.片区ID) ?? null,
)

const preview = computed(() =>
  previewBatch(currentDistrict.value?.限值, {
    余氯: form.余氯,
    浊度: form.浊度,
    pH: form.pH,
  }),
)

const reasonOk = computed(() => form.超标原因.trim().length >= 5)

function verdictClass(verdict: string | null): string {
  if (verdict === '超标') return 'v-bad'
  if (verdict === '预警') return 'v-warn'
  if (verdict === '达标') return 'v-ok'
  return ''
}

function onPointChange() {
  // 切换采样点即切换片区口径，preview 是 computed，会自动按新口径重算
}

const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  if (!form.采样点ID) {
    error.value = '请选择采样点'
    return
  }
  if (!form.采样时间 || !form.采样人员.trim()) {
    error.value = '采样时间与采样人员为必填项'
    return
  }
  if (!preview.value.ready) {
    error.value = '请把余氯、浊度、pH 三个指标都录成不小于 0 的数值'
    return
  }
  if (preview.value.conclusion === '超标' && !reasonOk.value) {
    error.value = '判定为超标，必须写清不少于 5 个字的原因才能保存'
    return
  }
  const values: Record<string, unknown> = {
    采样人员: form.采样人员.trim(),
    采样时间: form.采样时间,
    余氯: Number(form.余氯),
    浊度: Number(form.浊度),
    pH: Number(form.pH),
    超标原因: form.超标原因.trim(),
  }
  busy.value = true
  try {
    const result =
      props.mode === 'edit' && props.sample
        ? await updateSample(props.sample.id, values)
        : await createSample({ 采样点ID: form.采样点ID, ...values })
    if (!result.ok) {
      error.value = result.message
      return
    }
    emit('saved', result.message)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '采样批次保存失败'
  } finally {
    busy.value = false
  }
}
</script>
