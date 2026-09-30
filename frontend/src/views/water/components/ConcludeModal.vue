<template>
  <ModalShell :title="`出具结论：${sample?.编号 ?? ''}`" width="560px" @close="$emit('close')">
    <table class="detail-table" v-if="sample">
      <tbody>
        <tr><th>采样点</th><td>{{ sample.采样点编号 }} · {{ sample.采样点名称 }}（{{ sample.片区 }}）</td></tr>
        <tr><th>采样时间</th><td>{{ sample.采样时间 }}</td></tr>
        <tr>
          <th>指标实测</th>
          <td>
            <span v-for="metric in metrics" :key="metric" class="metric-chip">
              {{ metric }} {{ sample[metric] }}
              <em :class="verdictClass(sample.指标结果[metric])">{{ sample.指标结果[metric] }}</em>
            </span>
          </td>
        </tr>
        <tr>
          <th>当前判定</th>
          <td><b :class="verdictClass(sample.结论)">{{ sample.结论 }}</b>（按 {{ sample.判定依据版本 }}）</td>
        </tr>
        <tr v-if="sample.超标原因"><th>已填原因</th><td>{{ sample.超标原因 }}</td></tr>
      </tbody>
    </table>
    <p class="form-tip">
      出具后将按片区<b>现行口径</b>把各指标判定与批次结论快照锁定留档；之后口径再调整，本批次也不会被改写。
    </p>
    <label class="form-row" v-if="sample?.结论 === '超标'">
      <span class="danger">超标原因 <b>*</b></span>
      <textarea
        v-model="reason"
        rows="3"
        :placeholder="sample.超标原因 ? '已填原因可直接沿用，也可补充修订' : '判定为超标，必须写清不少于 5 个字的原因才能出具结论'"
      ></textarea>
    </label>
    <p class="form-tip danger" v-if="sample?.结论 === '超标' && !reasonOk">
      判定为超标，写清不少于 5 个字的原因后才能出具结论。
    </p>
    <p v-if="error" class="error-text">{{ error }}</p>
    <template #footer>
      <button class="btn ghost" type="button" @click="$emit('close')">取消</button>
      <button class="btn primary" type="button" :disabled="busy" @click="submit">出具并锁定留档</button>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { concludeSample, METRICS, type WaterSample } from '@/api/water'
import ModalShell from './ModalShell.vue'

const props = defineProps<{ sample: WaterSample }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', message: string): void
}>()

const metrics = [...METRICS]
const reason = ref(props.sample.超标原因 ?? '')
const error = ref('')
const busy = ref(false)
const reasonOk = () => reason.value.trim().length >= 5

function verdictClass(verdict?: string): string {
  if (verdict === '超标') return 'v-bad'
  if (verdict === '预警') return 'v-warn'
  if (verdict === '达标') return 'v-ok'
  return ''
}

async function submit() {
  error.value = ''
  if (props.sample.结论 === '超标' && !reasonOk()) {
    error.value = '判定为超标，必须写清不少于 5 个字的原因才能出具结论'
    return
  }
  busy.value = true
  try {
    const result = await concludeSample(props.sample.id, reason.value.trim())
    if (!result.ok) {
      error.value = result.message
      return
    }
    emit('saved', result.message)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '结论出具失败'
  } finally {
    busy.value = false
  }
}
</script>
