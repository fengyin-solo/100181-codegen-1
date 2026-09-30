<template>
  <ModalShell title="登记采样点" width="520px" @close="$emit('close')">
    <label class="form-row">
      <span>采样点编号 <b>*</b></span>
      <input v-model="form.采样点编号" placeholder="例如：WQ-007" />
    </label>
    <label class="form-row">
      <span>采样点名称 <b>*</b></span>
      <input v-model="form.采样点名称" placeholder="例如：城北出厂水" />
    </label>
    <label class="form-row">
      <span>所属片区 <b>*</b></span>
      <select v-model="form.片区ID">
        <option :value="null" disabled>请选择片区</option>
        <option v-for="district in districts" :key="district.id" :value="district.id">
          {{ district.片区名称 }}（现行 V{{ district.现行版本 }}）
        </option>
      </select>
    </label>
    <label class="form-row">
      <span>采样位置</span>
      <input v-model="form.位置" placeholder="例如：城北水厂出水口" />
    </label>
    <p class="form-tip" v-if="currentDistrict">
      该采样点与指标录入共用同一份口径：{{ currentDistrict.限值摘要 }}
    </p>
    <p v-if="error" class="error-text">{{ error }}</p>
    <template #footer>
      <button class="btn ghost" type="button" @click="$emit('close')">取消</button>
      <button class="btn primary" type="button" :disabled="busy" @click="submit">登记</button>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import { createPoint, type WaterDistrict } from '@/api/water'
import ModalShell from './ModalShell.vue'

const props = defineProps<{ districts: WaterDistrict[] }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', message: string): void
}>()

const form = reactive({
  采样点编号: '',
  采样点名称: '',
  片区ID: null as number | null,
  位置: '',
})
const error = ref('')
const busy = ref(false)

const currentDistrict = computed(() =>
  props.districts.find((item) => item.id === form.片区ID) ?? null,
)

async function submit() {
  error.value = ''
  if (!form.采样点编号.trim() || !form.采样点名称.trim()) {
    error.value = '采样点编号与采样点名称为必填项'
    return
  }
  if (!form.片区ID) {
    error.value = '请选择所属片区'
    return
  }
  busy.value = true
  try {
    const result = await createPoint({
      采样点编号: form.采样点编号.trim(),
      采样点名称: form.采样点名称.trim(),
      片区ID: form.片区ID,
      位置: form.位置.trim(),
    })
    if (!result.ok) {
      error.value = result.message
      return
    }
    emit('saved', result.message)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '采样点登记失败'
  } finally {
    busy.value = false
  }
}
</script>
