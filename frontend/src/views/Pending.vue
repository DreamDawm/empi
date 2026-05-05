<template>
  <div class="pending-page">
    <div class="page-header">
      <div class="header-info">
        <h1>待审核合并</h1>
        <span class="count-badge">{{ total }} 条记录</span>
      </div>
      <button class="refresh-btn" @click="loadCandidates">
        <span>⟳</span>
      </button>
    </div>

    <div class="candidates-list" v-if="candidates.length">
      <div v-for="item in candidates" :key="item.id" class="candidate-card">
        <div class="patient-info">
          <div class="patient-avatar">{{ getInitials(item.patient_a?.patient_name) }}</div>
          <div class="patient-detail">
            <span class="patient-name">{{ item.patient_a?.patient_name }}</span>
            <span class="patient-id">ID: {{ item.patient_a?.patient_id }}</span>
          </div>
        </div>

        <div class="similarity-badge" :class="getScoreClass(item.similarity_score)">
          <span class="score-value">{{ item.similarity_score }}</span>
          <span class="score-label">分</span>
        </div>

        <div class="merge-icon">⇄</div>

        <div class="patient-info">
          <div class="patient-avatar secondary">{{ getInitials(item.patient_b?.patient_name) }}</div>
          <div class="patient-detail">
            <span class="patient-name">{{ item.patient_b?.patient_name }}</span>
            <span class="patient-id">ID: {{ item.patient_b?.patient_id }}</span>
          </div>
        </div>

        <div class="card-actions">
          <button class="action-btn merge" @click="handleMerge(item)">
            <span>合并</span>
          </button>
          <button class="action-btn ignore" @click="handleIgnore(item)">
            <span>忽略</span>
          </button>
        </div>
      </div>

      <div class="pagination-container" v-if="total > pageSize">
        <button
          class="page-btn"
          :disabled="page === 1"
          @click="page--; loadCandidates()"
        >
          ◀
        </button>
        <span class="page-info">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button
          class="page-btn"
          :disabled="page >= Math.ceil(total / pageSize)"
          @click="page++; loadCandidates()"
        >
          ▶
        </button>
      </div>
    </div>

    <div v-else class="empty-state">
      <span class="empty-icon">◐</span>
      <span class="empty-text">暂无待审核记录</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { mergeApi, configApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const candidates = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const pendingThreshold = ref(60)

const getInitials = (name) => {
  if (!name) return '?'
  return name.slice(0, 2)
}

const getScoreClass = (score) => {
  if (score >= 80) return 'high'
  if (score >= 60) return 'medium'
  return 'low'
}

onMounted(async () => {
  try {
    const res = await configApi.getPendingThreshold()
    pendingThreshold.value = res.data.threshold || 60
  } catch (error) {
    console.error('获取待审核阈值失败', error)
  }
  loadCandidates()
})

const loadCandidates = async () => {
  try {
    const res = await mergeApi.listCandidates(page.value, pageSize.value, pendingThreshold.value)
    candidates.value = res.data.data || []
    total.value = res.data.total || 0
  } catch (error) {
    ElMessage.error('获取待审核列表失败')
  }
}

const handleMerge = async (row) => {
  try {
    await ElMessageBox.confirm('确认合并这两个患者？', '合并确认', { type: 'warning' })
    await mergeApi.merge(row.patient_a.patient_id, row.patient_b.patient_id)
    ElMessage.success('合并成功')
    loadCandidates()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('合并失败')
    }
  }
}

const handleIgnore = async (row) => {
  try {
    await ElMessageBox.confirm('确认忽略此候选对？', '忽略确认', { type: 'warning' })
    await mergeApi.ignore(row.id)
    ElMessage.success('已忽略')
    loadCandidates()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}
</script>

<style scoped>
.pending-page {
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

.refresh-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 16px;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
}

.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.candidate-card {
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  backdrop-filter: blur(8px);
  transition: transform 0.2s ease;
}

.candidate-card:hover {
  transform: translateX(4px);
}

.patient-info {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
}

.patient-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--accent-indigo);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.patient-avatar.secondary {
  background: var(--accent-amber);
}

.patient-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.patient-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.patient-id {
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.similarity-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  min-width: 72px;
}

.similarity-badge.high {
  background: rgba(16, 185, 129, 0.15);
  color: var(--accent-emerald);
}

.similarity-badge.medium {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-amber);
}

.similarity-badge.low {
  background: rgba(107, 114, 128, 0.15);
  color: var(--text-secondary);
}

.score-value {
  font-family: 'DM Serif Display', serif;
  font-size: 24px;
  line-height: 1;
}

.score-label {
  font-size: 11px;
  margin-top: 2px;
}

.merge-icon {
  font-size: 24px;
  color: var(--text-muted);
}

.card-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  padding: 10px 18px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid;
}

.action-btn.merge {
  background: var(--accent-emerald-dim);
  border-color: var(--accent-emerald);
  color: var(--accent-emerald);
}

.action-btn.merge:hover {
  background: var(--accent-emerald);
  color: white;
}

.action-btn.ignore {
  background: transparent;
  border-color: var(--border-color);
  color: var(--text-secondary);
}

.action-btn.ignore:hover {
  background: rgba(255, 255, 255, 0.04);
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
  font-variant-numeric: tabular-nums;
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