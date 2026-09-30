/** 水质采样检测台账接口封装：片区、版本化限值口径、采样点、采样批次与统计。 */
import { request } from '@/api/client'

export interface Bound {
  min: number | null
  warn_min: number | null
  warn_max: number | null
  max: number | null
}

/** 一版口径：每个指标一组限值；单侧指标（浊度）允许下限为 null。 */
export type LimitsDoc = Record<string, Bound>

export interface WaterDistrict {
  id: number
  片区编号: string
  片区名称: string
  现行版本: number | null
  现行口径ID: number | null
  生效时间: string | null
  限值: LimitsDoc
  限值摘要: string
}

export interface StandardVersion {
  id: number
  版本: number
  版本号: string
  生效时间: string
  限值: LimitsDoc
  限值摘要: string
  备注: string
  是否现行: boolean
}

export interface WaterPoint {
  id: number
  采样点编号: string
  采样点名称: string
  片区ID: number
  片区: string
  位置: string
  启用: boolean
  采样点状态: string
  现行版本: string
  现行口径: string
}

export interface MetricResult {
  指标: string
  数值: number
  单位: string
  结果: '达标' | '预警' | '超标'
}

export interface WaterSample {
  id: number
  编号: string
  采样点ID: number
  采样点编号: string
  采样点名称: string
  片区ID: number
  片区: string
  采样时间: string
  采样人员: string
  余氯: string
  浊度: string
  pH: string
  指标结果: Record<string, string>
  结论: '达标' | '预警' | '超标'
  判定状态: '待判定' | '已判定'
  判定依据版本: string
  判定依据口径ID: number
  口径说明: string
  超标原因: string
  需补原因: boolean
  最近一次: string
  readings: Record<string, number>
  pending: boolean
  abnormal: boolean
}

export interface PagePayload<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface WaterStats {
  cards: { label: string; value: number }[]
  超标列表: WaterSample[]
  超标批次数: number
  列表总条数: number
}

export interface ActionResponse {
  ok: boolean
  message: string
  entry?: Record<string, unknown> | null
}

export interface SampleFilters {
  keyword?: string
  district_id?: number | null
  point_id?: number | null
  result?: string | null
  status?: string | null
  latest_only?: boolean
}

export const METRICS = ['余氯', '浊度', 'pH'] as const
export const METRIC_UNITS: Record<string, string> = { 余氯: 'mg/L', 浊度: 'NTU', pH: '' }
export const LIMIT_KEYS = ['min', 'warn_min', 'warn_max', 'max'] as const
export const LIMIT_LABELS: Record<string, string> = {
  min: '合格下限',
  warn_min: '预警下限',
  warn_max: '预警上限',
  max: '合格上限',
}

function buildQuery(filters: SampleFilters): string {
  const params = new URLSearchParams()
  if (filters.keyword) params.set('keyword', filters.keyword)
  if (filters.district_id) params.set('district_id', String(filters.district_id))
  if (filters.point_id) params.set('point_id', String(filters.point_id))
  if (filters.result) params.set('result', filters.result)
  if (filters.status) params.set('status', filters.status)
  if (filters.latest_only) params.set('latest_only', 'true')
  return params.toString()
}

async function readAction(response: Response): Promise<ActionResponse> {
  const payload = (await response.json()) as ActionResponse
  if (!response.ok) throw new Error(payload.message || '操作未生效')
  return payload
}

export async function fetchDistricts(): Promise<WaterDistrict[]> {
  const response = await request('/api/water/districts')
  if (!response.ok) throw new Error('片区列表读取失败')
  return ((await response.json()) as { items: WaterDistrict[] }).items
}

export async function fetchStandards(districtId: number): Promise<StandardVersion[]> {
  const response = await request(`/api/water/districts/${districtId}/standards`)
  if (!response.ok) throw new Error('口径版本链读取失败')
  return ((await response.json()) as { items: StandardVersion[] }).items
}

export async function fetchPoints(districtId?: number | null, keyword?: string): Promise<WaterPoint[]> {
  const params = new URLSearchParams()
  if (districtId) params.set('district_id', String(districtId))
  if (keyword) params.set('keyword', keyword)
  const response = await request(`/api/water/points?${params.toString()}`)
  if (!response.ok) throw new Error('采样点列表读取失败')
  return ((await response.json()) as { items: WaterPoint[] }).items
}

export async function fetchSamples(
  filters: SampleFilters,
  page = 1,
  size = 200,
): Promise<PagePayload<WaterSample>> {
  const query = buildQuery(filters)
  const response = await request(`/api/water/samples?page=${page}&size=${size}&${query}`)
  if (!response.ok) throw new Error('采样台账读取失败')
  return (await response.json()) as PagePayload<WaterSample>
}

export async function fetchStats(filters: SampleFilters): Promise<WaterStats> {
  const response = await request(`/api/water/stats?${buildQuery(filters)}`)
  if (!response.ok) throw new Error('统计数据读取失败')
  return (await response.json()) as WaterStats
}

export async function createDistrict(name: string): Promise<ActionResponse> {
  return submit('/api/water/districts', { 片区名称: name })
}

export async function adjustStandard(
  districtId: number,
  limits: LimitsDoc,
  remark: string,
): Promise<ActionResponse> {
  const response = await request(`/api/water/districts/${districtId}/standards`, {
    method: 'POST',
    body: JSON.stringify({ values: { 限值: limits }, remark }),
  })
  return readAction(response)
}

export async function createPoint(values: Record<string, unknown>): Promise<ActionResponse> {
  return submit('/api/water/points', values)
}

export async function setPointStatus(pointId: number, active: boolean): Promise<ActionResponse> {
  return submit(`/api/water/points/${pointId}/status`, { 启用: active })
}

export async function createSample(values: Record<string, unknown>): Promise<ActionResponse> {
  return submit('/api/water/samples', values)
}

export async function updateSample(sampleId: number, values: Record<string, unknown>): Promise<ActionResponse> {
  const response = await request(`/api/water/samples/${sampleId}`, {
    method: 'PATCH',
    body: JSON.stringify({ values }),
  })
  return readAction(response)
}

export async function concludeSample(sampleId: number, reason: string): Promise<ActionResponse> {
  return submit(`/api/water/samples/${sampleId}/conclude`, { 超标原因: reason })
}

async function submit(path: string, values: Record<string, unknown>): Promise<ActionResponse> {
  const response = await request(path, {
    method: 'POST',
    body: JSON.stringify({ values }),
  })
  return readAction(response)
}
