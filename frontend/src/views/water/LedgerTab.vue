<template>
  <div>
    <div class="filter-bar">
      <label class="filter-item">
        <span>关键字</span>
        <input v-model="filters.keyword" placeholder="批次编号 / 采样点" @keyup.enter="reload" />
      </label>
      <label class="filter-item">
        <span>片区</span>
        <select v-model="filters.district_id" @change="onDistrictChange">
          <option :value="null">全部片区</option>
          <option v-for="district in districts" :key="district.id" :value="district.id">
            {{ district.片区名称 }}
          </option>
        </select>
      </label>
      <label class="filter-item">
        <span>采样点</span>
        <select v-model="filters.point_id">
          <option :value="null">全部采样点</option>
          <option v-for="point in pointOptions" :key="point.id" :value="point.id">
            {{ point.采样点编号 }} · {{ point.采样点名称 }}
          </option>
        </select>
      </label>
      <label class="filter-item">
        <span>结论</span>
        <select v-model="filters.result">
          <option :value="null">全部结论</option>
          <option value="达标">达标</option>
          <option value="预警">预警</option>
          <option value="超标">超标</option>
        </select>
      </label>
      <label class="filter-item">
        <span>判定状态</span>
        <select v-model="filters.status">
          <option :value="null">全部</option>
          <option value="待判定">待判定</option>
          <option value="已判定">已判定（留档）</option>
        </select>
      </label>
      <label class="filter-check">
        <input v-model="filters.latest_only" type="checkbox" @change="reload" />
        只看每个采样点最近一次
      </label>
      <button class="btn" type="button" @click="reload">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置</button>
      <button class="btn primary" type="button" @click="openCreate">登记采样批次</button>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td>
            {{ row.编号 }}
            <span v-if="row.最近一次" class="tag latest">最近一次</span>
          </td>
          <td>{{ row.采样点编号 }} · {{ row.采样点名称 }}</td>
          <td>{{ row.片区 }}</td>
          <td>{{ row.采样时间 }}</td>
          <td>{{ row.采样人员 }}</td>
          <td v-for="metric in metrics" :key="metric">
            <span :class="verdictClass(row.指标结果[metric])">{{ row[metric] }}</span>
          </td>
          <td>
            <span class="result-pill" :class="verdictClass(row.结论)">{{ row.结论 }}</span>
            <div class="cell-sub">{{ row.判定状态 }}</div>
          </td>
          <td>
            {{ row.判定依据版本 }}
            <div class="cell-sub muted" :title="row.超标原因">
              <template v-if="row.结论 === '超标'">
                <span class="danger">{{ row.需补原因 ? '待补原因' : '原因已填' }}</span>
                {{ row.超标原因 }}
              </template>
            </div>
          </td>
          <td class="row-actions">
            <template v-if="row.判定状态 === '待判定'">
              <button class="link" type="button" @click="openEdit(row)">改录</button>
              <button class="link" type="button" @click="openConclude(row)">出具结论</button>
            </template>
            <span v-else class="muted">已留档锁定</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">当前筛选条件下暂无采样记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条记录，同一采样点按采样时间前后排列</span>
      <span v-if="message" class="ok-text">{{ message }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <SampleModal
      v-if="sampleModal"
      :mode="sampleModal.mode"
      :sample="sampleModal.sample"
      :districts="districts"
      :points="allPoints"
      @close="sampleModal = null"
      @saved="onSaved"
    />
    <ConcludeModal
      v-if="concluding"
      :sample="concluding"
      @close="concluding = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  fetchDistricts,
  fetchPoints,
  fetchSamples,
  METRICS,
  type SampleFilters,
  type WaterDistrict,
  type WaterPoint,
  type WaterSample,
} from '@/api/water'
import SampleModal from './components/SampleModal.vue'
import ConcludeModal from './components/ConcludeModal.vue'

const columns = ['批次编号', '采样点', '片区', '采样时间', '采样人员', ...METRICS, '结论 / 状态', '判定依据 / 超标原因']
const metrics = [...METRICS]

const districts = ref<WaterDistrict[]>([])
const allPoints = ref<WaterPoint[]>([])
const rows = ref<WaterSample[]>([])
const total = ref(0)
const errorMessage = ref('')
const message = ref('')

const filters = reactive<SampleFilters>({
  keyword: '',
  district_id: null,
  point_id: null,
  result: null,
  status: null,
  latest_only: false,
})

const sampleModal = ref<{ mode: 'create' | 'edit'; sample: WaterSample | null } | null>(null)
const concluding = ref<WaterSample | null>(null)

const pointOptions = computed(() =>
  filters.district_id
    ? allPoints.value.filter((point) => point.片区ID === filters.district_id)
    : allPoints.value,
)

function verdictClass(verdict?: string): string {
  if (verdict === '超标') return 'v-bad'
  if (verdict === '预警') return 'v-warn'
  if (verdict === '达标') return 'v-ok'
  return ''
}

function onDistrictChange() {
  filters.point_id = null
  void reload()
}

function resetFilters() {
  filters.keyword = ''
  filters.district_id = null
  filters.point_id = null
  filters.result = null
  filters.status = null
  filters.latest_only = false
  void reload()
}

function openCreate() {
  sampleModal.value = { mode: 'create', sample: null }
}

function openEdit(row: WaterSample) {
  sampleModal.value = { mode: 'edit', sample: row }
}

function openConclude(row: WaterSample) {
  concluding.value = row
}

async function onSaved(text: string) {
  message.value = text
  sampleModal.value = null
  concluding.value = null
  await reload()
}

async function reload() {
  errorMessage.value = ''
  try {
    const payload = await fetchSamples(filters, 1, 200)
    rows.value = payload.items
    total.value = payload.total
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '采样台账读取失败'
  }
}

onMounted(async () => {
  try {
    const [districtRows, pointRows] = await Promise.all([fetchDistricts(), fetchPoints()])
    districts.value = districtRows
    allPoints.value = pointRows
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '基础数据读取失败'
  }
  await reload()
})

defineExpose({ reload, filters })
</script>
