<template>
  <div class="patients-page">
    <div class="search-section">
      <div class="search-box">
        <span class="search-icon">⌕</span>
        <input
          v-model="searchId"
          type="text"
          placeholder="输入患者ID查询..."
          class="search-input"
          @keyup.enter="searchPatient"
        />
        <button class="search-btn" @click="searchPatient">查询</button>
      </div>
    </div>

    <div v-if="patient" class="patient-result">
      <div class="patient-header">
        <div class="patient-avatar">{{ getInitials(patient.patient_name) }}</div>
        <div class="patient-identity">
          <span class="patient-name">{{ patient.patient_name }}</span>
          <span class="patient-id">ID: {{ patient.patient_id }}</span>
        </div>
        <span class="status-tag" :class="patient.status === 'NORMAL' ? 'normal' : 'merged'">
          {{ patient.status === 'NORMAL' ? '正常' : '已合并' }}
        </span>
      </div>

      <div class="info-grid" v-if="masterInfo">
        <div class="info-card">
          <span class="info-label">主索引ID</span>
          <span class="info-value">{{ masterInfo.master_id }}</span>
        </div>
        <div class="info-card">
          <span class="info-label">主患者</span>
          <span class="info-value">{{ masterInfo.primary_patient?.patient_name || '-' }}</span>
        </div>
      </div>

      <div v-if="masterInfo?.merged_patients?.length" class="merged-section">
        <span class="section-label">已合并患者</span>
        <div class="merged-tags">
          <span v-for="p in masterInfo.merged_patients" :key="p.patient_id" class="merged-tag">
            {{ p.patient_name }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="!patient && searched" class="empty-state">
      <span class="empty-icon">◇</span>
      <span class="empty-text">未找到该患者</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { patientsApi } from '../api'
import { ElMessage } from 'element-plus'

const searchId = ref('')
const patient = ref(null)
const masterInfo = ref(null)
const searched = ref(false)

const getInitials = (name) => {
  if (!name) return '?'
  return name.slice(0, 2)
}

const searchPatient = async () => {
  if (!searchId.value) {
    ElMessage.warning('请输入患者ID')
    return
  }
  try {
    patient.value = await patientsApi.get(searchId.value)
    const masterRes = await patientsApi.getMaster(searchId.value)
    masterInfo.value = masterRes.data
    searched.value = true
  } catch (error) {
    ElMessage.error('患者不存在')
    patient.value = null
    masterInfo.value = null
    searched.value = true
  }
}
</script>

<style scoped>
.patients-page {
  max-width: 700px;
}

.search-section {
  margin-bottom: 32px;
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 4px;
  backdrop-filter: blur(8px);
}

.search-icon {
  font-size: 18px;
  color: var(--text-muted);
  padding: 0 16px;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 15px;
  padding: 14px 0;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-btn {
  padding: 12px 24px;
  background: var(--accent-emerald);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.search-btn:hover {
  opacity: 0.9;
}

.patient-result {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 28px;
  backdrop-filter: blur(8px);
}

.patient-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.patient-avatar {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: var(--accent-indigo);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
}

.patient-identity {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.patient-name {
  font-size: 18px;
  font-weight: 500;
}

.patient-id {
  font-size: 13px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.status-tag {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

.status-tag.normal {
  background: var(--accent-emerald-dim);
  color: var(--accent-emerald);
}

.status-tag.merged {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-amber);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.info-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-label {
  font-size: 12px;
  color: var(--text-muted);
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.merged-section {
  border-top: 1px solid var(--border-color);
  padding-top: 20px;
}

.section-label {
  font-size: 12px;
  color: var(--text-muted);
  display: block;
  margin-bottom: 12px;
}

.merged-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.merged-tag {
  padding: 6px 14px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  font-size: 13px;
  color: var(--accent-indigo);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 60px 0;
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