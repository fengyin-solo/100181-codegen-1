<template>
  <section class="page water-page">
    <header class="page-head">
      <div>
        <h2>水质采样检测台账</h2>
        <p class="page-desc">采样点按片区维护；采样批次按当前片区限值自动判定，超标原因必填，已出结论按历史版本留档。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openSampleForm()">登记采样批次</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in statCards" :key="item.label" class="stat-card water-stat">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </article>
    </div>

    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-button"
        :class="{ active: activeTab === tab.key }"
        type="button"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="activeTab === 'samples'">
      <form class="filter-bar" @submit.prevent="reloadSamples">
        <label class="filter-item">
          <span>片区</span>
          <select v-model.number="sampleFilters.area_id" @change="onFilterAreaChange">
            <option :value="undefined">全部片区</option>
            <option v-for="area in areas" :key="area.id" :value="area.id">{{ area.name }}</option>
          </select>
        </label>
        <label class="filter-item">
          <span>采样点</span>
          <select v-model.number="sampleFilters.point_id">
            <option :value="undefined">全部采样点</option>
            <option v-for="point in visiblePoints" :key="point.id" :value="point.id">{{ point.name }}</option>
          </select>
        </label>
        <label class="filter-item">
          <span>结论</span>
          <select v-model="sampleFilters.result">
            <option value="">全部结论</option>
            <option v-for="result in resultOptions" :key="result" :value="result">{{ result }}</option>
          </select>
        </label>
        <label class="filter-item">
          <span>关键字</span>
          <input v-model="sampleFilters.keyword" placeholder="批次/采样点/人员" />
        </label>
        <button class="btn" type="submit">查询</button>
        <button class="btn ghost" type="button" @click="resetSampleFilters">重置</button>
      </form>

      <table class="data-table">
        <thead>
          <tr>
            <th>时间排列</th>
            <th>批次号</th>
            <th>片区</th>
            <th>采样点</th>
            <th>采样时间</th>
            <th>余氯</th>
            <th>浊度</th>
            <th>pH</th>
            <th>结论</th>
            <th>判定口径</th>
            <th>超标原因</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in samples" :key="row.id" :class="resultClass(row.result)">
            <td>
              <span v-if="row.is_latest" class="latest-tag">最近一次</span>
              <span v-else>历史</span>
            </td>
            <td>{{ row.batch_no }}</td>
            <td>{{ row.area_name }}</td>
            <td>{{ row.point_name }}</td>
            <td>{{ formatTime(row.sampled_at) }}</td>
            <td v-for="code in metricCodes" :key="code">
              <span :class="['metric', metricLevel(row, code)]">{{ formatMetric(row, code) }}</span>
            </td>
            <td><span class="result-pill" :class="resultClass(row.result)">{{ row.result }}</span></td>
            <td>{{ row.standard_version || (row.preview_standard_version ? `待判定（${row.preview_standard_version}）` : '未配置') }}</td>
            <td>{{ row.reason || (row.result === '超标' ? '—' : '') }}</td>
            <td>
              <button v-if="!row.finalized" class="link" type="button" @click="openSampleForm(row)">补录/出结论</button>
              <span v-else class="muted-text">已留档</span>
            </td>
          </tr>
          <tr v-if="!samples.length">
            <td colspan="12" class="empty-state">暂无采样批次，可先登记一条检测记录</td>
          </tr>
        </tbody>
      </table>
      <footer class="page-foot">
        <span>共 {{ sampleTotal }} 条采样记录，按采样时间从近到远排列</span>
        <span v-if="message" :class="messageOk ? '' : 'error-text'">{{ message }}</span>
      </footer>
    </div>

    <div v-else-if="activeTab === 'stats'" class="stats-panel">
      <article class="exceed-card">
        <div class="card-head">
          <div>
            <span class="stat-label">超标批次卡片</span>
            <strong>{{ stats.exceeded }}</strong>
            <span class="muted-text">条，和采样列表按“超标”筛选后的条数一致</span>
          </div>
          <button class="btn" type="button" @click="showExceededInLedger">在采样列表查看</button>
        </div>
      </article>
      <table class="data-table">
        <thead>
          <tr>
            <th>批次号</th><th>片区</th><th>采样点</th><th>采样时间</th><th>超标指标</th><th>原因</th><th>口径版本</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in stats.exceeded_items" :key="row.id">
            <td>{{ row.batch_no }}</td>
            <td>{{ row.area_name }}</td>
            <td>{{ row.point_name }}</td>
            <td>{{ formatTime(row.sampled_at) }}</td>
            <td>{{ exceededMetricNames(row) }}</td>
            <td>{{ row.reason }}</td>
            <td>{{ row.standard_version }}</td>
          </tr>
          <tr v-if="!stats.exceeded_items?.length">
            <td colspan="7" class="empty-state">当前筛选条件下暂无超标批次</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="activeTab === 'points'">
      <div class="config-grid">
        <form class="side-form" @submit.prevent="saveArea">
          <h3>{{ areaForm.id ? '编辑片区' : '新增片区' }}</h3>
          <label><span>片区名称</span><input v-model="areaForm.name" /></label>
          <label><span>负责人</span><input v-model="areaForm.manager" /></label>
          <label><span>备注</span><input v-model="areaForm.remark" /></label>
          <button class="btn primary" type="submit">保存片区</button>
          <button class="btn ghost" type="button" @click="resetAreaForm">清空</button>
        </form>
        <table class="data-table">
          <thead><tr><th>片区</th><th>负责人</th><th>当前口径</th><th>备注</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="area in areas" :key="area.id">
              <td>{{ area.name }}</td>
              <td>{{ area.manager || '—' }}</td>
              <td>{{ area.current_version || '未发布' }}</td>
              <td>{{ area.remark || '—' }}</td>
              <td><button class="link" type="button" @click="editArea(area)">编辑</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="config-grid separated">
        <form class="side-form" @submit.prevent="savePoint">
          <h3>{{ pointForm.id ? '编辑采样点' : '新增采样点' }}</h3>
          <label><span>所属片区</span>
            <select v-model.number="pointForm.area_id" required>
              <option :value="undefined">请选择片区</option>
              <option v-for="area in areas" :key="area.id" :value="area.id">{{ area.name }}</option>
            </select>
          </label>
          <label><span>采样点编号</span><input v-model="pointForm.code" /></label>
          <label><span>采样点名称</span><input v-model="pointForm.name" /></label>
          <label><span>地址</span><input v-model="pointForm.address" /></label>
          <label><span>联系人</span><input v-model="pointForm.contact" /></label>
          <p class="muted-text">采样点选择片区后，与该片区指标录入共用同一份限值口径：{{ pointStandardVersion }}</p>
          <button class="btn primary" type="submit">保存采样点</button>
          <button class="btn ghost" type="button" @click="resetPointForm">清空</button>
        </form>
        <table class="data-table">
          <thead><tr><th>编号</th><th>采样点</th><th>片区</th><th>口径</th><th>地址</th><th>联系人</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="point in points" :key="point.id">
              <td>{{ point.code }}</td><td>{{ point.name }}</td><td>{{ point.area_name }}</td><td>{{ point.current_version || '未发布' }}</td>
              <td>{{ point.address || '—' }}</td><td>{{ point.contact || '—' }}</td>
              <td><button class="link" type="button" @click="editPoint(point)">编辑</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="standards-panel">
      <form class="standard-form" @submit.prevent="saveStandard">
        <h3>发布片区新版限值口径</h3>
        <p class="muted-text">调整限值会生成新版本；尚未出结论且指标完整的批次立即按新版本重算，已有结论不被改写。</p>
        <div class="form-row">
          <label><span>片区</span>
            <select v-model.number="standardForm.area_id" @change="fillDefaultIndicators" required>
              <option :value="undefined">请选择片区</option>
              <option v-for="area in areas" :key="area.id" :value="area.id">
                {{ area.name }}（当前 {{ area.current_version || '未发布' }}）
              </option>
            </select>
          </label>
          <label><span>调整说明</span><input v-model="standardForm.note" placeholder="如：浊度预警收紧" /></label>
        </div>
        <table class="data-table indicator-table">
          <thead><tr><th>指标</th><th>单位</th><th>预警下限</th><th>预警上限</th><th>超标下限</th><th>超标上限</th></tr></thead>
          <tbody>
            <tr v-for="(indicator, index) in standardForm.indicators" :key="index">
              <td><input v-model="indicator.name" /></td>
              <td><input v-model="indicator.unit" /></td>
              <td><input v-model.number="indicator.warning_low" type="number" step="0.01" /></td>
              <td><input v-model.number="indicator.warning_high" type="number" step="0.01" /></td>
              <td><input v-model.number="indicator.limit_low" type="number" step="0.01" /></td>
              <td><input v-model.number="indicator.limit_high" type="number" step="0.01" /></td>
            </tr>
          </tbody>
        </table>
        <button class="btn primary" type="submit">发布新版本并重算未判定批次</button>
      </form>

      <table class="data-table">
        <thead><tr><th>片区</th><th>版本</th><th>状态</th><th>指标</th><th>发布时间</th><th>说明</th></tr></thead>
        <tbody>
          <tr v-for="standard in standards" :key="standard.id" :class="{ current: standard.is_current }">
            <td>{{ standard.area_name }}</td>
            <td>{{ standard.version }}</td>
            <td>{{ standard.is_current ? '当前口径' : '历史留档' }}</td>
            <td>{{ standard.indicators.map((item: Indicator) => item.name).join('、') }}</td>
            <td>{{ standard.created_at }}</td>
            <td>{{ standard.note }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="sampleDialog.open" class="modal-mask" @click.self="sampleDialog.open = false">
      <form class="modal-card" @submit.prevent="submitSample(true)">
        <h3>{{ sampleDialog.id ? '补录采样批次' : '登记采样批次' }}</h3>
        <div class="form-row">
          <label><span>采样点</span>
            <select v-model.number="sampleForm.point_id" @change="onSamplePointChange" required>
              <option :value="undefined">请选择采样点</option>
              <option v-for="point in points" :key="point.id" :value="point.id">{{ point.area_name }} / {{ point.name }}</option>
            </select>
          </label>
          <label><span>采样时间</span><input v-model="sampleForm.sampled_at" type="datetime-local" required /></label>
          <label><span>采样人员</span><input v-model="sampleForm.sampler" required /></label>
        </div>
        <p class="muted-text">判定口径：{{ activeStandardVersion }}，指标必须全部录完才能出结论。</p>
        <table class="data-table indicator-table">
          <thead><tr><th>指标</th><th>检测值</th><th>单位</th><th>当前预判</th></tr></thead>
          <tbody>
            <tr v-for="indicator in activeIndicators" :key="indicator.code">
              <td>{{ indicator.name }}</td>
              <td><input v-model.number="sampleForm.values[indicator.code]" type="number" step="0.01" /></td>
              <td>{{ indicator.unit }}</td>
              <td><span class="result-pill" :class="previewLevel(indicator)">{{ previewLevel(indicator) }}</span></td>
            </tr>
          </tbody>
        </table>
        <label class="reason-box">
          <span>超标原因（预判为超标时必填）</span>
          <textarea v-model="sampleForm.reason" rows="3" placeholder="请写清超标原因，例如外部施工、二次供水水箱污染等"></textarea>
        </label>
        <p v-if="draftPreview === '超标' && !sampleForm.reason.trim()" class="error-text">当前检测值超标，必须填写原因后才能保存结论；也可先存为草稿。</p>
        <div class="modal-actions">
          <button class="btn" type="button" @click="submitSample(false)">先存草稿</button>
          <button class="btn primary" type="submit">保存并出结论</button>
          <button class="btn ghost" type="button" @click="sampleDialog.open = false">取消</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { fetchJson, sendJson } from '@/api/client'

type Id = number
type Result = '待判定' | '达标' | '预警' | '超标'

type Area = {
  id: Id
  name: string
  manager: string
  remark: string
  current_version?: string | null
  current_standard_id?: Id | null
}

type Point = {
  id: Id
  code: string
  name: string
  area_id: Id
  area_name: string
  address: string
  contact: string
  current_version?: string | null
}

type Indicator = {
  code: string
  name: string
  unit: string
  warning_low: number
  warning_high: number
  limit_low: number
  limit_high: number
}

type Standard = {
  id: Id
  area_id: Id
  area_name: string
  version: string
  is_current: boolean
  note: string
  created_at: string
  indicators: Indicator[]
}

type MetricResult = {
  code: string
  name: string
  unit: string
  value: number
  level: Result
}

type Sample = {
  id: Id
  batch_no: string
  point_id: Id
  area_id: Id
  area_name: string
  point_name: string
  sampled_at: string
  sampler: string
  values: Record<string, number>
  result: Result
  finalized: boolean
  reason: string
  standard_version?: string | null
  preview_result?: Result
  preview_standard_version?: string | null
  metric_results?: MetricResult[]
  preview_metric_results?: MetricResult[]
  is_latest?: boolean
}

type Page<T> = { items: T[]; total: number }
type ActionResponse = { ok: boolean; message: string; entry?: unknown }
type Stats = {
  total: number
  pending: number
  qualified: number
  warning: number
  exceeded: number
  exceeded_items: Sample[]
}

const tabs: { key: 'samples' | 'points' | 'standards' | 'stats'; label: string }[] = [
  { key: 'samples', label: '采样台账' },
  { key: 'points', label: '片区与采样点' },
  { key: 'standards', label: '限值口径版本' },
  { key: 'stats', label: '统计' },
]
const resultOptions: Result[] = ['达标', '预警', '超标', '待判定']
const metricCodes = ['residual_chlorine', 'turbidity', 'ph']

const activeTab = ref<'samples' | 'points' | 'standards' | 'stats'>('samples')
const areas = ref<Area[]>([])
const points = ref<Point[]>([])
const standards = ref<Standard[]>([])
const samples = ref<Sample[]>([])
const sampleTotal = ref(0)
const message = ref('')
const messageOk = ref(true)
const stats = ref<Stats>({ total: 0, pending: 0, qualified: 0, warning: 0, exceeded: 0, exceeded_items: [] })

const sampleFilters = reactive<{ area_id?: number; point_id?: number; result: string; keyword: string }>({
  area_id: undefined,
  point_id: undefined,
  result: '',
  keyword: '',
})

const areaForm = reactive({ id: undefined as Id | undefined, name: '', manager: '', remark: '' })
const pointForm = reactive({ id: undefined as Id | undefined, area_id: undefined as Id | undefined, code: '', name: '', address: '', contact: '' })

const defaultIndicators = (): Indicator[] => [
  { code: 'residual_chlorine', name: '余氯', unit: 'mg/L', warning_low: 0.3, warning_high: 1.2, limit_low: 0.1, limit_high: 2 },
  { code: 'turbidity', name: '浊度', unit: 'NTU', warning_low: 0, warning_high: 1, limit_low: 0, limit_high: 3 },
  { code: 'ph', name: 'pH', unit: '', warning_low: 7, warning_high: 8, limit_low: 6.5, limit_high: 8.5 },
]

const standardForm = reactive<{ area_id?: Id; note: string; indicators: Indicator[] }>({
  area_id: undefined,
  note: '',
  indicators: defaultIndicators(),
})

const sampleDialog = reactive({ open: false, id: undefined as Id | undefined })
const sampleForm = reactive<{ point_id?: Id; sampled_at: string; sampler: string; values: Record<string, number | undefined>; reason: string }>({
  point_id: undefined,
  sampled_at: '',
  sampler: '',
  values: {},
  reason: '',
})

const visiblePoints = computed(() => {
  if (!sampleFilters.area_id) return points.value
  return points.value.filter((point) => point.area_id === sampleFilters.area_id)
})

const statCards = computed(() => [
  { label: '采样批次', value: stats.value.total, note: '当前筛选条件' },
  { label: '待判定', value: stats.value.pending, note: '指标未录完或待补原因' },
  { label: '预警批次', value: stats.value.warning, note: '进入预警区间' },
  { label: '超标批次', value: stats.value.exceeded, note: '卡片明细条数一致' },
])

const selectedPoint = computed(() => points.value.find((point) => point.id === sampleForm.point_id))
const activeStandard = computed<Standard | undefined>(() => {
  const areaId = selectedPoint.value?.area_id ?? standardForm.area_id
  return standards.value.find((standard) => standard.area_id === areaId && standard.is_current)
})
const activeIndicators = computed<Indicator[]>(() => activeStandard.value?.indicators ?? [])
const activeStandardVersion = computed(() => activeStandard.value?.version ?? '该片区尚未发布')
const pointStandardVersion = computed(() => {
  const area = areas.value.find((item) => item.id === pointForm.area_id)
  return area?.current_version ?? '未发布'
})
const draftPreview = computed<Result>(() => evaluateDraft().result)

function setMessage(text: string, ok = true) {
  message.value = text
  messageOk.value = ok
}

async function loadBaseData() {
  const [areaPayload, pointPayload, standardPayload] = await Promise.all([
    fetchJson<{ items: Area[] }>('/api/water-quality/areas'),
    fetchJson<{ items: Point[] }>('/api/water-quality/points'),
    fetchJson<{ items: Standard[] }>('/api/water-quality/standards'),
  ])
  areas.value = areaPayload.items
  points.value = pointPayload.items
  standards.value = standardPayload.items
}

function sampleQuery(includeResult = true) {
  const params = new URLSearchParams()
  if (sampleFilters.area_id) params.set('area_id', String(sampleFilters.area_id))
  if (sampleFilters.point_id) params.set('point_id', String(sampleFilters.point_id))
  if (includeResult && sampleFilters.result) params.set('result', sampleFilters.result)
  if (sampleFilters.keyword) params.set('keyword', sampleFilters.keyword)
  params.set('size', '200')
  return params.toString()
}

async function reloadSamples() {
  const payload = await fetchJson<Page<Sample>>(`/api/water-quality/samples?${sampleQuery()}`)
  samples.value = payload.items
  sampleTotal.value = payload.total
}

async function reloadStats() {
  stats.value = await fetchJson<Stats>(`/api/water-quality/samples/stats?${sampleQuery(false)}`)
}

async function reloadAll() {
  await loadBaseData()
  await Promise.all([reloadSamples(), reloadStats()])
}

function onFilterAreaChange() {
  sampleFilters.point_id = undefined
}

function resetSampleFilters() {
  sampleFilters.area_id = undefined
  sampleFilters.point_id = undefined
  sampleFilters.result = ''
  sampleFilters.keyword = ''
  void reloadSamples()
  void reloadStats()
}

async function handleAction(response: ActionResponse, closeDialog = false) {
  if (!response.ok) {
    setMessage(response.message, false)
    return
  }
  setMessage(response.message)
  if (closeDialog) sampleDialog.open = false
  await reloadAll()
}

async function saveArea() {
  try {
    const path = areaForm.id ? `/api/water-quality/areas/${areaForm.id}` : '/api/water-quality/areas'
    const method = areaForm.id ? 'PUT' : 'POST'
    const response = await sendJson<ActionResponse>(path, method, { values: { ...areaForm } })
    await handleAction(response)
    resetAreaForm()
  } catch (error) {
    setMessage(error instanceof Error ? error.message : '片区保存失败', false)
  }
}

function editArea(area: Area) {
  Object.assign(areaForm, { id: area.id, name: area.name, manager: area.manager, remark: area.remark })
}

function resetAreaForm() {
  Object.assign(areaForm, { id: undefined, name: '', manager: '', remark: '' })
}

async function savePoint() {
  try {
    const path = pointForm.id ? `/api/water-quality/points/${pointForm.id}` : '/api/water-quality/points'
    const method = pointForm.id ? 'PUT' : 'POST'
    const response = await sendJson<ActionResponse>(path, method, { values: { ...pointForm } })
    await handleAction(response)
    resetPointForm()
  } catch (error) {
    setMessage(error instanceof Error ? error.message : '采样点保存失败', false)
  }
}

function editPoint(point: Point) {
  Object.assign(pointForm, {
    id: point.id,
    area_id: point.area_id,
    code: point.code,
    name: point.name,
    address: point.address,
    contact: point.contact,
  })
}

function resetPointForm() {
  Object.assign(pointForm, { id: undefined, area_id: undefined, code: '', name: '', address: '', contact: '' })
}

function fillDefaultIndicators() {
  const current = standards.value.find((item) => item.area_id === standardForm.area_id && item.is_current)
  standardForm.indicators = current
    ? current.indicators.map((item) => ({ ...item }))
    : defaultIndicators()
}

async function saveStandard() {
  try {
    const response = await sendJson<ActionResponse>('/api/water-quality/standards', 'POST', { values: { ...standardForm } })
    await handleAction(response)
    standardForm.area_id = undefined
    standardForm.note = ''
    standardForm.indicators = defaultIndicators()
  } catch (error) {
    setMessage(error instanceof Error ? error.message : '限值版本发布失败', false)
  }
}

function onSamplePointChange() {
  sampleForm.values = {}
  const point = points.value.find((item) => item.id === sampleForm.point_id)
  const standard = standards.value.find((item) => item.area_id === point?.area_id && item.is_current)
  ;(standard?.indicators ?? []).forEach((indicator) => {
    sampleForm.values[indicator.code] = undefined
  })
}

function openSampleForm(row?: Sample) {
  sampleDialog.open = true
  sampleDialog.id = row?.id
  sampleForm.point_id = row?.point_id
  sampleForm.sampled_at = row?.sampled_at ? row.sampled_at.slice(0, 16) : ''
  sampleForm.sampler = row?.sampler ?? ''
  sampleForm.reason = row?.reason ?? ''
  sampleForm.values = {}
  const point = points.value.find((item) => item.id === sampleForm.point_id)
  const standard = standards.value.find((item) => item.area_id === point?.area_id && item.is_current)
  ;(standard?.indicators ?? []).forEach((indicator) => {
    sampleForm.values[indicator.code] = row?.values?.[indicator.code]
  })
  if (!row) onSamplePointChange()
}

async function submitSample(finalize: boolean) {
  if (!sampleForm.point_id || !sampleForm.sampled_at || !sampleForm.sampler) {
    setMessage('请选择采样点并填写采样时间、采样人员', false)
    return
  }
  try {
    const values = {
      point_id: sampleForm.point_id,
      sampled_at: sampleForm.sampled_at,
      sampler: sampleForm.sampler,
      reason: sampleForm.reason,
      values: sampleForm.values,
      finalize,
    }
    const path = sampleDialog.id ? `/api/water-quality/samples/${sampleDialog.id}` : '/api/water-quality/samples'
    const method = sampleDialog.id ? 'PUT' : 'POST'
    const response = await sendJson<ActionResponse>(path, method, { values })
    await handleAction(response, true)
  } catch (error) {
    setMessage(error instanceof Error ? error.message : '采样批次保存失败', false)
  }
}

function evaluateIndicator(indicator: Indicator, value: number | undefined): Result {
  if (value === undefined || Number.isNaN(value)) return '待判定'
  if (value < indicator.limit_low || value > indicator.limit_high) return '超标'
  if (value < indicator.warning_low || value > indicator.warning_high) return '预警'
  return '达标'
}

function evaluateDraft(): { result: Result; levels: Record<string, Result> } {
  const levels: Record<string, Result> = {}
  let result: Result = '达标'
  for (const indicator of activeIndicators.value) {
    const level = evaluateIndicator(indicator, sampleForm.values[indicator.code])
    levels[indicator.code] = level
    if (level === '待判定') result = '待判定'
    if (result !== '待判定' && level === '超标') result = '超标'
    if (result === '达标' && level === '预警') result = '预警'
  }
  return { result, levels }
}

function previewLevel(indicator: Indicator): Result {
  return evaluateDraft().levels[indicator.code] ?? '待判定'
}

function metricLevel(row: Sample, code: string): string {
  const results = row.finalized ? row.metric_results : row.preview_metric_results
  return results?.find((item) => item.code === code)?.level ?? ''
}

function formatMetric(row: Sample, code: string) {
  const value = row.values?.[code]
  return value === undefined || value === null ? '—' : Number(value).toFixed(2)
}

function exceededMetricNames(row: Sample) {
  return row.metric_results?.filter((item) => item.level === '超标').map((item) => item.name).join('、') || '—'
}

function formatTime(value: string) {
  return value ? value.replace('T', ' ') : '—'
}

function resultClass(result: Result) {
  return { 达标: 'qualified', 预警: 'warning', 超标: 'exceeded', 待判定: 'pending' }[result]
}

function showExceededInLedger() {
  activeTab.value = 'samples'
  sampleFilters.result = '超标'
  void reloadSamples()
}

onMounted(async () => {
  try {
    await reloadAll()
  } catch (error) {
    setMessage(error instanceof Error ? error.message : '水质采样数据加载失败', false)
  }
})
</script>
