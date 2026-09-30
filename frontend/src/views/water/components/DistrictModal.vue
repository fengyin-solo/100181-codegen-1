<template>
  <ModalShell :title="title" width="760px" @close="$emit('close')">
    <!-- 新建片区 -->
    <template v-if="mode === 'create'">
      <label class="form-row">
        <span>片区名称 <b>*</b></span>
        <input v-model="name" placeholder="例如：城北片区" />
      </label>
      <p class="form-tip">
        新片区自动生成第一版限值口径（采用平台初始限值），建好后可在「片区与口径」里随时调整，
        每次调整都会留下一个新版本。
      </p>
    </template>

    <!-- 调整口径：以现行版本为底稿，提交后生成新版本，旧版本原样留档 -->
    <template v-else-if="mode === 'adjust' && district">
      <p class="form-tip">
        {{ district.片区名称 }} 当前现行口径为
        <b>V{{ district.现行版本 }}</b>（{{ district.生效时间 }} 生效）。
        保存后生成新版本并立即生效：<b>尚未出具结论</b>的采样记录按新版重算，
        <b>已出具结论</b>的记录按当时那一版留档、不会被改写。
      </p>
      <LimitEditor
        ref="editorRef"
        v-model="limits"
        v-model:remark="remark"
        show-remark
      />
    </template>

    <!-- 版本链 -->
    <template v-else-if="mode === 'versions'">
      <div v-for="version in versions" :key="version.id" class="version-item" :class="{ current: version.是否现行 }">
        <div class="version-head">
          <strong>{{ version.版本号 }}</strong>
          <span class="tag" v-if="version.是否现行">现行</span>
          <span class="tag archived" v-else>已留档</span>
          <span class="muted">{{ version.生效时间 }}</span>
        </div>
        <div class="muted">{{ version.限值摘要 }}</div>
        <div class="muted" v-if="version.备注">说明：{{ version.备注 }}</div>
      </div>
      <p v-if="!versions.length" class="empty-state">该片区还没有口径版本</p>
    </template>

    <p v-if="error" class="error-text">{{ error }}</p>

    <template #footer>
      <button class="btn ghost" type="button" @click="$emit('close')">取消</button>
      <button v-if="mode === 'create'" class="btn primary" type="button" :disabled="busy" @click="submitCreate">
        建立片区
      </button>
      <button v-else-if="mode === 'adjust'" class="btn primary" type="button" :disabled="busy" @click="submitAdjust">
        发布新版本
      </button>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import {
  adjustStandard,
  createDistrict,
  type LimitsDoc,
  type StandardVersion,
  type WaterDistrict,
} from '@/api/water'
import LimitEditor from './LimitEditor.vue'
import ModalShell from './ModalShell.vue'

type Mode = 'create' | 'adjust' | 'versions'

const props = withDefaults(
  defineProps<{
    mode: Mode
    district?: WaterDistrict | null
    versions?: StandardVersion[]
  }>(),
  { district: null, versions: () => [] },
)
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', message: string): void
}>()

const title = {
  create: '新建片区',
  adjust: `调整限值口径：${props.district?.片区名称 ?? ''}`,
  versions: `口径版本留档：${props.district?.片区名称 ?? ''}`,
}[props.mode]

const defaultLimits: LimitsDoc = {
  余氯: { min: 0.05, warn_min: 0.1, warn_max: 0.3, max: 0.5 },
  浊度: { min: null, warn_min: null, warn_max: 0.5, max: 1.0 },
  pH: { min: 6.5, warn_min: 6.8, warn_max: 8.0, max: 8.5 },
}

const name = ref('')
const limits = ref<LimitsDoc>(
  props.district ? JSON.parse(JSON.stringify(props.district.限值)) as LimitsDoc : defaultLimits,
)
const remark = ref('')
const editorRef = ref<InstanceType<typeof LimitEditor> | null>(null)
const error = ref('')
const busy = ref(false)

async function submitCreate() {
  error.value = ''
  if (!name.value.trim()) {
    error.value = '片区名称为必填项'
    return
  }
  busy.value = true
  try {
    const result = await createDistrict(name.value.trim())
    if (!result.ok) {
      error.value = result.message
      return
    }
    emit('saved', result.message)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '片区建立失败'
  } finally {
    busy.value = false
  }
}

async function submitAdjust() {
  error.value = ''
  const doc = editorRef.value?.normalized() ?? limits.value
  busy.value = true
  try {
    const result = await adjustStandard(props.district!.id, doc, remark.value.trim())
    if (!result.ok) {
      error.value = result.message
      return
    }
    emit('saved', result.message)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '口径发布失败'
  } finally {
    busy.value = false
  }
}
</script>
