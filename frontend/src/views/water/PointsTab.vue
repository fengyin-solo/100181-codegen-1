<template>
  <div>
    <div class="filter-bar">
      <label class="filter-item">
        <span>所属片区</span>
        <select v-model="districtId" @change="reload">
          <option :value="null">全部片区</option>
          <option v-for="district in districts" :key="district.id" :value="district.id">
            {{ district.片区名称 }}
          </option>
        </select>
      </label>
      <label class="filter-item">
        <span>检索</span>
        <input v-model="keyword" placeholder="编号 / 名称 / 位置" @keyup.enter="reload" />
      </label>
      <button class="btn" type="button" @click="reload">查询</button>
      <button class="btn primary" type="button" @click="creating = true">登记采样点</button>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>采样点编号</th>
          <th>采样点名称</th>
          <th>所属片区</th>
          <th>采样位置</th>
          <th>状态</th>
          <th>共用限值口径（与指标录入同一份）</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="point in rows" :key="point.id">
          <td>{{ point.采样点编号 }}</td>
          <td>{{ point.采样点名称 }}</td>
          <td>{{ point.片区 }}</td>
          <td>{{ point.位置 || '—' }}</td>
          <td>
            <span class="tag" :class="point.启用 ? 'ok' : 'archived'">{{ point.采样点状态 }}</span>
          </td>
          <td class="muted">{{ point.现行版本 }}：{{ point.现行口径 }}</td>
          <td class="row-actions">
            <button v-if="point.启用" class="link" type="button" @click="toggle(point, false)">停用</button>
            <button v-else class="link" type="button" @click="toggle(point, true)">启用</button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td colspan="7" class="empty-state">暂无采样点，先在片区下登记采样点</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ rows.length }} 个采样点，按片区维护</span>
      <span v-if="message" class="ok-text">{{ message }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <PointModal
      v-if="creating"
      :districts="districts"
      @close="creating = false"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  fetchDistricts,
  fetchPoints,
  setPointStatus,
  type WaterDistrict,
  type WaterPoint,
} from '@/api/water'
import PointModal from './components/PointModal.vue'

const districts = ref<WaterDistrict[]>([])
const rows = ref<WaterPoint[]>([])
const districtId = ref<number | null>(null)
const keyword = ref('')
const creating = ref(false)
const errorMessage = ref('')
const message = ref('')

async function reload() {
  errorMessage.value = ''
  try {
    rows.value = await fetchPoints(districtId.value, keyword.value || undefined)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '采样点读取失败'
  }
}

async function toggle(point: WaterPoint, active: boolean) {
  errorMessage.value = ''
  try {
    const result = await setPointStatus(point.id, active)
    if (!result.ok) {
      errorMessage.value = result.message
      return
    }
    message.value = result.message
    await reload()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '采样点状态更新失败'
  }
}

async function onSaved(text: string) {
  message.value = text
  creating.value = false
  await reload()
}

onMounted(async () => {
  districts.value = await fetchDistricts()
  await reload()
})

defineExpose({ reload })
</script>
