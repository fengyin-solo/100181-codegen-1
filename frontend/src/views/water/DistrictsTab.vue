<template>
  <div>
    <div class="filter-bar">
      <p class="filter-tip">限值口径按片区各留一版：每次调整新增一个版本，待判定记录按新版重算，已出结论记录按当时版本留档。</p>
      <button class="btn primary" type="button" @click="openCreate">新建片区</button>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>片区编号</th>
          <th>片区名称</th>
          <th>现行版本</th>
          <th>生效时间</th>
          <th>现行限值口径</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="district in rows" :key="district.id">
          <td>{{ district.片区编号 }}</td>
          <td>{{ district.片区名称 }}</td>
          <td><span class="tag ok">V{{ district.现行版本 }}</span></td>
          <td>{{ district.生效时间 }}</td>
          <td class="muted">{{ district.限值摘要 }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openAdjust(district)">调整口径（出新版）</button>
            <button class="link" type="button" @click="openVersions(district)">查看版本链</button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td colspan="6" class="empty-state">暂无片区，先新建片区并建立第一版口径</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ rows.length }} 个片区，每个片区独立维护自己的限值口径</span>
      <span v-if="message" class="ok-text">{{ message }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <DistrictModal
      v-if="modal"
      :mode="modal.mode"
      :district="modal.district ?? null"
      :versions="modal.versions ?? []"
      @close="modal = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  fetchDistricts,
  fetchStandards,
  type StandardVersion,
  type WaterDistrict,
} from '@/api/water'
import DistrictModal from './components/DistrictModal.vue'

const rows = ref<WaterDistrict[]>([])
const errorMessage = ref('')
const message = ref('')
const modal = ref<{
  mode: 'create' | 'adjust' | 'versions'
  district?: WaterDistrict
  versions?: StandardVersion[]
} | null>(null)

async function reload() {
  errorMessage.value = ''
  try {
    rows.value = await fetchDistricts()
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '片区列表读取失败'
  }
}

function openCreate() {
  modal.value = { mode: 'create' }
}

function openAdjust(district: WaterDistrict) {
  modal.value = { mode: 'adjust', district }
}

async function openVersions(district: WaterDistrict) {
  modal.value = { mode: 'versions', district, versions: [] }
  try {
    modal.value.versions = await fetchStandards(district.id)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '版本链读取失败'
  }
}

async function onSaved(text: string) {
  message.value = text
  modal.value = null
  await reload()
}

onMounted(reload)

defineExpose({ reload })
</script>
