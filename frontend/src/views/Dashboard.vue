<template>
  <div class="dashboard">
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in statsDisplay" :key="stat.label">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-indicator" :style="{ background: stat.color }"></div>
      </div>
    </div>

    <div class="dashboard-section">
      <div class="section-header">
        <h2>合并趋势</h2>
        <span class="section-sub">近7日数据</span>
      </div>
      <div class="trend-chart" v-if="trendData.length">
        <div class="chart-bars">
          <div
            v-for="(item, index) in trendData"
            :key="item.date"
            class="bar-container"
          >
            <div
              class="bar"
              :style="{
                height: getBarHeight(item.count) + '%',
                animationDelay: index * 0.1 + 's'
              }"
            ></div>
            <span class="bar-label">{{ formatDate(item.date) }}</span>
            <span class="bar-value">{{ item.count }}</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        <span class="empty-icon">◇</span>
        <span>暂无数据</span>
      </div>
    </div>

    <div class="dashboard-section">
      <div class="section-header">
        <h2>数据清洗</h2>
      </div>
      <div class="clean-actions">
        <button class="clean-btn primary" @click="handleClean" :disabled="cleaning">
          <span class="btn-icon">⟳</span>
          <span>{{ cleaning ? '清洗中...' : '立刻增量清洗' }}</span>
        </button>
        <button class="clean-btn warning" @click="handleFullClean" :disabled="fullCleaning">
          <span class="btn-icon">⟲</span>
          <span>{{ fullCleaning ? '全量清洗中...' : '立刻全量清洗' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { statsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const stats = ref({ total: 0, merged: 0, pending: 0, merge_rate: 0 })
const trendData = ref([])
const maxCount = ref(1)
const cleaning = ref(false)
const fullCleaning = ref(false)

const statsDisplay = computed(() => [
  { label: '患者总数', value: stats.value.total || 0, color: 'var(--accent-indigo)' },
  { label: '已合并', value: stats.value.merged || 0, color: 'var(--accent-emerald)' },
  { label: '待审核', value: stats.value.pending || 0, color: 'var(--accent-amber)' },
  { label: '合并率', value: (stats.value.merge_rate || 0) + '%', color: 'var(--accent-emerald)' }
])

const getBarHeight = (count) => (count / maxCount.value) * 100

const formatDate = (dateStr) => {
  const d = new Date(dateStr)
  return (d.getMonth() + 1) + '/' + d.getDate()
}

onMounted(async () => {
  try {
    const [statsRes, trendRes] = await Promise.all([
      statsApi.get(),
      statsApi.getTrend(7)
    ])
    stats.value = statsRes.data
    trendData.value = trendRes.data.data || []
    maxCount.value = Math.max(...trendData.value.map(d => d.count), 1)
  } catch (error) {
    console.error('获取统计数据失败', error)
  }
})

const handleClean = async () => {
  try {
    cleaning.value = true
    const res = await statsApi.triggerClean()
    ElMessage.success(res.data.message || '清洗完成')
    const statsRes = await statsApi.get()
    stats.value = statsRes.data
  } catch (error) {
    ElMessage.error('清洗失败')
  } finally {
    cleaning.value = false
  }
}

const handleFullClean = async () => {
  try {
    await ElMessageBox.confirm(
      '全量清洗将重新处理所有数据，确定要继续吗？',
      '全量清洗确认',
      { type: 'warning' }
    )
    fullCleaning.value = true
    const res = await statsApi.triggerFullClean()
    ElMessage.success(res.data.message || '全量清洗完成')
    const statsRes = await statsApi.get()
    stats.value = statsRes.data
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('全量清洗失败')
    }
  } finally {
    fullCleaning.value = false
  }
}
</script>

<style scoped>
.dashboard {
  max-width: 1200px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(8px);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-soft);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  font-weight: 500;
}

.stat-value {
  font-family: 'DM Serif Display', serif;
  font-size: 32px;
  font-weight: 400;
  color: var(--text-primary);
}

.stat-indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.dashboard-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 28px;
  margin-bottom: 20px;
  backdrop-filter: blur(8px);
}

.section-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 24px;
}

.section-header h2 {
  font-family: 'DM Serif Display', serif;
  font-size: 18px;
  font-weight: 400;
}

.section-sub {
  font-size: 12px;
  color: var(--text-muted);
}

.trend-chart {
  height: 200px;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 160px;
  gap: 12px;
}

.bar-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  gap: 8px;
}

.bar {
  width: 100%;
  background: linear-gradient(180deg, var(--accent-emerald) 0%, rgba(16, 185, 129, 0.4) 100%);
  border-radius: 6px 6px 0 0;
  margin-top: auto;
  animation: barGrow 0.6s ease-out both;
  min-height: 4px;
}

@keyframes barGrow {
  from {
    transform: scaleY(0);
    transform-origin: bottom;
  }
  to {
    transform: scaleY(1);
  }
}

.bar-label {
  font-size: 11px;
  color: var(--text-muted);
}

.bar-value {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  height: 160px;
}

.empty-icon {
  font-size: 24px;
  opacity: 0.5;
}

.clean-actions {
  display: flex;
  gap: 16px;
}

.clean-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clean-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.04);
}

.clean-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.clean-btn.primary {
  border-color: var(--accent-emerald);
  color: var(--accent-emerald);
}

.clean-btn.primary:hover:not(:disabled) {
  background: var(--accent-emerald-dim);
}

.clean-btn.warning {
  border-color: var(--accent-amber);
  color: var(--accent-amber);
}

.clean-btn.warning:hover:not(:disabled) {
  background: rgba(245, 158, 11, 0.1);
}

.btn-icon {
  font-size: 16px;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>