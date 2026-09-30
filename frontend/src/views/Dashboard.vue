<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card" :class="{ highlight: card.label === '水质超标批次' }">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <section class="exceed-summary">
      <div class="summary-head">
        <div>
          <h3>超标批次卡片</h3>
          <p>当前共 <strong>{{ waterStats.exceeded }}</strong> 条，口径与采样台账“超标”筛选后的条数一致。</p>
        </div>
        <RouterLink class="btn" to="/water-quality">进入水质台账</RouterLink>
      </div>
      <table class="data-table" v-if="waterStats.exceeded_items?.length">
        <thead>
          <tr><th>批次号</th><th>片区</th><th>采样点</th><th>采样时间</th><th>超标原因</th><th>口径版本</th></tr>
        </thead>
        <tbody>
          <tr v-for="item in waterStats.exceeded_items" :key="item.id">
            <td>{{ item.batch_no }}</td>
            <td>{{ item.area_name }}</td>
            <td>{{ item.point_name }}</td>
            <td>{{ item.sampled_at.replace('T', ' ') }}</td>
            <td>{{ item.reason }}</td>
            <td>{{ item.standard_version }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-state">暂无超标批次</p>
    </section>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
}

type WaterStats = {
  exceeded: number
  exceeded_items: {
    id: number
    batch_no: string
    area_name: string
    point_name: string
    sampled_at: string
    reason: string
    standard_version: string
  }[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])
const waterStats = ref<WaterStats>({ exceeded: 0, exceeded_items: [] })

onMounted(async () => {
  try {
    const [payload, stats] = await Promise.all([
      fetchJson<Overview>('/api/overview'),
      fetchJson<WaterStats>('/api/water-quality/samples/stats'),
    ])
    cards.value = payload.cards
    moduleRows.value = payload.modules
    waterStats.value = stats
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}, {"label": "水质超标批次", "value": 0}]
    moduleRows.value = []
  }
})
</script>
