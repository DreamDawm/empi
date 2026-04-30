<template>
  <div class="merged-page">
    <div class="page-header">
      <div class="header-info">
        <h1>合并历史</h1>
        <span class="count-badge">{{ total }} 条记录</span>
      </div>
    </div>

    <div class="history-list" v-if="history.length">
      <div v-for="item in history" :key="item.id" class="history-card">
        <div class="history-main">
          <div class="patient-pair">
            <span class="patient-tag">{{ item.person_id_a }}</span>
            <span class="arrow">→</span>
            <span class="patient-tag">{{ item.person_id_b }}</span>
          </div>
          <div class="master-id">
            <span class="master-label">主索引</span>
            <span class="master-value">{{ item.master_id }}</span>
          </div>
        </div>
        <div class="history-meta">
          <span class="merge-type" :class="item.merge_type?.toLowerCase()">
            {{ item.merge_type === 'AUTO' ? '自动' : '人工' }}
          </span>
          <span class="similarity">{{ item.similarity_score }}分</span>
          <span class="time">{{ formatTime(item.merge_time) }}</span>
        </div>
      </div>

      <div class="pagination-container" v-if="total > pageSize">
        <button class="page-btn" :disabled="page === 1" @click="page--; loadHistory()">◀</button>
        <span class="page-info">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button class="page-btn" :disabled="page >= Math.ceil(total / pageSize)" @click="page++; loadHistory()">▶</button>
      </div>
    </div>

    <div v-else class="empty-state">
      <span class="empty-icon">◐</span>
      <span class="empty-text">暂无合并记录</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { mergeApi } from '../api'
import { ElMessage } from 'element-plus'

const history = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const formatTime = (timeStr) => {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadHistory()
})

const loadHistory = async () => {
  try {
    const res = await mergeApi.history(page.value, pageSize.value)
    history.value = res.data.data || []
    total.value = res.data.total || 0
  } catch (error) {
    ElMessage.error('获取合并历史失败')
  }
}
</script>

<style scoped>
.merged-page {
  max-width: 900px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.header-info {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.header-info h1 {
  font-family: 'DM Serif Display', serif;
  font-size: 24px;
  font-weight: 400;
}

.count-badge {
  font-size: 13px;
  color: var(--text-muted);
  padding: 4px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 20px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 18px 24px;
  backdrop-filter: blur(8px);
}

.history-main {
  display: flex;
  align-items: center;
  gap: 32px;
}

.patient-pair {
  display: flex;
  align-items: center;
  gap: 10px;
}

.patient-tag {
  padding: 6px 14px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  font-size: 13px;
  color: var(--accent-indigo);
  font-variant-numeric: tabular-nums;
}

.arrow {
  color: var(--text-muted);
}

.master-id {
  display: flex;
  align-items: center;
  gap: 8px;
}

.master-label {
  font-size: 12px;
  color: var(--text-muted);
}

.master-value {
  font-size: 13px;
  color: var(--accent-emerald);
  font-variant-numeric: tabular-nums;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.merge-type {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.merge-type.auto {
  background: var(--accent-emerald-dim);
  color: var(--accent-emerald);
}

.merge-type.manual {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
}

.similarity {
  font-size: 13px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.time {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 120px;
}

.pagination-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-top: 24px;
}

.page-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.page-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
}

.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: var(--text-muted);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 0;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 48px;
  opacity: 0.4;
}

.empty-text {
  font-size: 14px;
}
</style>