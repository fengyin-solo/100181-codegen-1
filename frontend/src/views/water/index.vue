<template>
  <section class="page water-page" data-module="water">
    <header class="page-head">
      <div>
        <h2>水质采样检测台账</h2>
        <p class="page-desc">
          采样点按片区维护；每批登记采样时间与余氯、浊度、pH，系统按各片区现行限值口径给出
          达标 / 预警 / 超标结论，超标必须写清原因。口径调整只影响未出结论的记录，已出结论按当时版本留档。
        </p>
      </div>
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="switchTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </div>
    </header>

    <KeepAlive>
      <component
        :is="currentTab"
        :ref="(instance: unknown) => setTabRef(instance)"
      />
    </KeepAlive>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import LedgerTab from './LedgerTab.vue'
import PointsTab from './PointsTab.vue'
import DistrictsTab from './DistrictsTab.vue'
import StatsTab from './StatsTab.vue'

type TabKey = 'ledger' | 'points' | 'districts' | 'stats'
type Reloadable = { reload: () => Promise<void> | void }

const tabs: { key: TabKey; label: string }[] = [
  { key: 'ledger', label: '采样台账' },
  { key: 'points', label: '采样点维护' },
  { key: 'districts', label: '片区与口径' },
  { key: 'stats', label: '统计' },
]
const activeTab = ref<TabKey>('ledger')
const tabInstances = ref<Partial<Record<TabKey, Reloadable | null>>>({})

const tabComponents = {
  ledger: LedgerTab,
  points: PointsTab,
  districts: DistrictsTab,
  stats: StatsTab,
}
const currentTab = computed(() => tabComponents[activeTab.value])

function setTabRef(instance: unknown) {
  tabInstances.value[activeTab.value] = instance as Reloadable | null
}

async function switchTab(key: TabKey) {
  activeTab.value = key
  await nextTick()
  // 口径/点位可能在别的页签被调整或增删，切回来时重新拉取，保证看到的是最新口径下的结论
  await tabInstances.value[key]?.reload()
}
</script>
