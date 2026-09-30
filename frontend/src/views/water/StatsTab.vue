<template>
  <div>
    <div class="filter-bar">
      <label class="filter-item">
        <span>片区</span>
        <select v-model="filters.district_id" @change="onFilterChange">
          <option :value="null">全部片区</option>
          <option v-for="district in districts" :key="district.id" :value="district.id">
            {{ district.片区名称 }}
          </option>
        </select>
      </label>
      <label class="filter-item">
        <span>采样点</span>
        <select v-model="filters.point_id" @change="reload">
          <option :value="null">全部采样点</option>
          <option v-for="point in pointOptions" :key="point.id" :value="point.id">
            {{ point.采样点编号 }} · {{ point.采样点名称 }}
          </option>
        </select>
      </label>
      <label class="filter-item">
        <span>判定状态</span>
        <select v-model="filters.status" @change="reload">
          <option :value="null">全部</option>
          <option value="待判定">待判定</option>
          <option value="已判定">已判定（留档）</option>
        </select>
      </label>
      <label class="filter-check">
        <input v-model="filters.latest_only" type="checkbox" @change="reload" />
        只看每个采样点最近一次
      </label>
    </div>

    <div class="stat-row">
      <article
        v-for="card in cards"
        :key="card.label"
        class="stat-card"
        :class="card.label === '超标批次' ? 'stat-bad' : ''"
      >
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>

    <h3 class="block-title">超标批次卡片（{{ stats?.超标批次数 ?? 0 }} 条）</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>批次编号</th>
          <th>采样点</th>
          <th>片区</th>
          <th>采样时间</th>
          <th>余氯</th>
          <th>浊度</th>
          <th>pH</th>
          <th>结论</th>
          <th>判定状态 / 依据版本</th>
          <th>超标原因</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in exceedRows" :key="row.id">
          <td>
            {{ row.编号 }}
            <span v-if="row.最近一次" class="tag latest">最近一次</span>
          </td>
          <td>{{ row.采样点编号 }} · {{ row.采样点名称 }}</td>
          <td>{{ row.片区 }}</td>
          <td>{{ row.采样时间 }}</td>
          <td v-for="metric in metrics" :key="metric">
            <span :class="verdictClass(row.指标结果[metric])">{{ row[metric] }}</span>
          </td>
          <td><span class="result-pill v-bad">超标</span></td>
          <td>
            {{ row.判定状态 }}
            <div class="cell-sub muted">{{ row.判定依据版本 }}</div>
          </td>
          <td>
            <span :class="row.超标原因 ? '' : 'danger'">
              {{ row.超标原因 || (row.判定状态 === '待判定' ? '待补原因后出具结论' : '—') }}
            </span>
          </td>
        </tr>
        <tr v-if="!exceedRows.length">
          <td :colspan="10" class="empty-state">当前筛选条件下没有超标批次</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>
        对账：超标批次卡片 <b>{{ stats?.超标批次数 ?? 0 }}</b> 条，
        下方超标列表 <b>{{ exceedRows.length }}</b> 条，
        同口径采样列表 <b>{{ stats?.列表总条数 ?? 0 }}</b> 条 ——
        卡片条数与采样列表中的超标行数一致。
      </span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  fetchDistricts,
  fetchPoints,
  fetchStats,
  METRICS,
  type SampleFilters,
  type WaterDistrict,
  type WaterPoint,
  type WaterStats,
  type WaterSample,
} from '@/api/water'

const metrics = [...METRICS]
const districts = ref<WaterDistrict[]>([])
const allPoints = ref<WaterPoint[]>([])
const stats = ref<WaterStats | null>(null)
const errorMessage = ref('')

const filters = reactive<SampleFilters>({
  district_id: null,
  point_id: null,
  status: null,
  latest_only: false,
})

const cards = computed(() => stats.value?.cards ?? [])
const exceedRows = computed<WaterSample[]>(() => stats.value?.超标列表 ?? [])

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

function onFilterChange() {
  filters.point_id = null
  void reload()
}

async function reload() {
  errorMessage.value = ''
  try {
    stats.value = await fetchStats(filters)
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '统计数据读取失败'
  }
}

onMounted(async () => {
  const [districtRows, pointRows] = await Promise.all([fetchDistricts(), fetchPoints()])
  districts.value = districtRows
  allPoints.value = pointRows
  await reload()
})

defineExpose({ reload })
</script>
