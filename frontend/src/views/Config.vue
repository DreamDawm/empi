<template>
  <div class="config-page">
    <div class="config-section">
      <div class="section-header">
        <div class="header-left">
          <h2>字段权重配置</h2>
        </div>
        <button class="add-btn" @click="addField">
          <span>+</span> 添加字段
        </button>
      </div>

      <div class="weight-list">
        <div v-for="(item, index) in weights" :key="index" class="weight-row">
          <div class="weight-info">
            <span class="field-name">{{ item.display_name || item.field_name }}</span>
            <span class="field-key">{{ item.field_name }}</span>
          </div>
          <div class="weight-input-wrap">
            <input
              type="number"
              v-model="item.weight"
              min="0"
              max="100"
              class="weight-input"
            />
            <span class="weight-unit">分</span>
          </div>
          <div class="row-actions">
            <button class="action-btn edit" @click="editField(index)">编辑</button>
            <button class="action-btn delete" @click="removeField(index)">删除</button>
          </div>
        </div>
      </div>

      <div class="weight-footer">
        <div class="total-weight" :class="{ valid: totalWeight === 100, invalid: totalWeight !== 100 }">
          <span class="total-label">权重总分</span>
          <span class="total-value">{{ totalWeight }} / 100</span>
        </div>
        <button class="save-btn" :disabled="totalWeight !== 100" @click="saveWeights">
          保存权重
        </button>
      </div>
    </div>

    <div class="config-section">
      <h2 class="section-title">合并阈值配置</h2>
      <div class="threshold-list">
        <div class="threshold-row">
          <div class="threshold-info">
            <span class="threshold-name">自动合并阈值</span>
            <span class="threshold-desc">≥此分数自动合并</span>
          </div>
          <div class="threshold-input-wrap">
            <input type="number" v-model="threshold" min="0" max="100" class="threshold-input" />
            <span class="threshold-unit">分</span>
          </div>
        </div>
        <div class="threshold-row">
          <div class="threshold-info">
            <span class="threshold-name">待审核显示阈值</span>
            <span class="threshold-desc"><此分数不显示在待审核列表</span>
          </div>
          <div class="threshold-input-wrap">
            <input type="number" v-model="pendingThreshold" min="0" max="100" class="threshold-input" />
            <span class="threshold-unit">分</span>
          </div>
        </div>
      </div>
      <button class="save-btn secondary" @click="saveThreshold">保存阈值</button>
    </div>

    <div class="config-section">
      <h2 class="section-title">ETL轮询配置</h2>
      <div class="poll-row">
        <div class="poll-info">
          <span class="poll-name">轮询间隔</span>
        </div>
        <div class="poll-input-wrap">
          <input type="number" v-model="pollInterval" min="1" max="24" class="poll-input" />
          <span class="poll-unit">小时</span>
        </div>
      </div>
      <button class="save-btn secondary" @click="savePollInterval">保存配置</button>
    </div>

    <div class="dialog-overlay" v-if="showAddDialog || showEditDialog" @click.self="closeDialogs">
      <div class="dialog">
        <div class="dialog-header">
          <h3>{{ showEditDialog ? '编辑字段' : '添加字段' }}</h3>
          <button class="dialog-close" @click="closeDialogs">✕</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>数据库字段</label>
            <select v-model="dialogData.field_name" class="form-select">
              <option value="">请选择字段</option>
              <option v-for="field in availableFields" :key="field" :value="field">{{ field }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>显示名称</label>
            <input type="text" v-model="dialogData.display_name" placeholder="请输入显示名称" class="form-input" />
          </div>
          <div class="form-group">
            <label>权重</label>
            <input type="number" v-model="dialogData.weight" min="0" max="100" class="form-input" />
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn-cancel" @click="closeDialogs">取消</button>
          <button class="btn-confirm" @click="showEditDialog ? confirmEditField() : confirmAddField()">
            确定
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { configApi } from '../api'
import { ElMessage } from 'element-plus'

const weights = ref([])
const threshold = ref(85)
const pendingThreshold = ref(60)
const pollInterval = ref(2)
const availableFields = ref([])
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const editingIndex = ref(-1)

const dialogData = ref({ field_name: '', display_name: '', weight: 0 })

const totalWeight = computed(() => {
  return weights.value.reduce((sum, item) => sum + (item.weight || 0), 0)
})

onMounted(async () => {
  try {
    const [weightsRes, thresholdRes, pendingRes, pollRes, fieldsRes] = await Promise.all([
      configApi.getWeights(),
      configApi.getThreshold(),
      configApi.getPendingThreshold(),
      configApi.getPollInterval(),
      configApi.getPatientFields()
    ])
    weights.value = weightsRes.data
    threshold.value = thresholdRes.data.threshold
    pendingThreshold.value = pendingRes.data.threshold
    pollInterval.value = pollRes.data.hours || 2
    availableFields.value = fieldsRes.data.fields || []
  } catch (error) {
    console.error('获取配置失败', error)
  }
})

const addField = () => {
  dialogData.value = { field_name: '', display_name: '', weight: 0 }
  showAddDialog.value = true
}

const editField = (index) => {
  editingIndex.value = index
  dialogData.value = { ...weights.value[index] }
  showEditDialog.value = true
}

const closeDialogs = () => {
  showAddDialog.value = false
  showEditDialog.value = false
  editingIndex.value = -1
}

const confirmAddField = () => {
  if (!dialogData.value.field_name) {
    ElMessage.warning('请选择字段')
    return
  }
  if (!dialogData.value.display_name) {
    ElMessage.warning('请输入显示名称')
    return
  }
  weights.value.push({ ...dialogData.value })
  closeDialogs()
}

const confirmEditField = () => {
  if (!dialogData.value.field_name) {
    ElMessage.warning('请选择字段')
    return
  }
  if (!dialogData.value.display_name) {
    ElMessage.warning('请输入显示名称')
    return
  }
  weights.value[editingIndex.value] = { ...dialogData.value }
  closeDialogs()
}

const removeField = (index) => {
  weights.value.splice(index, 1)
}

const saveWeights = async () => {
  if (totalWeight.value !== 100) {
    ElMessage.error('权重总分必须等于100分')
    return
  }
  try {
    await configApi.updateWeights(weights.value)
    ElMessage.success('权重保存成功')
  } catch (error) {
    ElMessage.error('权重保存失败')
  }
}

const saveThreshold = async () => {
  try {
    await Promise.all([
      configApi.updateThreshold(threshold.value),
      configApi.updatePendingThreshold(pendingThreshold.value)
    ])
    ElMessage.success('阈值保存成功')
  } catch (error) {
    ElMessage.error('阈值保存失败')
  }
}

const savePollInterval = async () => {
  try {
    await configApi.updatePollInterval(pollInterval.value)
    ElMessage.success('轮询间隔保存成功')
  } catch (error) {
    ElMessage.error('轮询间隔保存失败')
  }
}
</script>

<style scoped>
.config-page {
  max-width: 800px;
}

.config-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 28px;
  margin-bottom: 20px;
  backdrop-filter: blur(8px);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  font-family: 'DM Serif Display', serif;
  font-size: 18px;
  font-weight: 400;
}

.section-title {
  font-family: 'DM Serif Display', serif;
  font-size: 18px;
  font-weight: 400;
  margin-bottom: 24px;
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  background: var(--accent-emerald-dim);
  border: 1px solid var(--accent-emerald);
  border-radius: var(--radius-md);
  color: var(--accent-emerald);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-btn:hover {
  background: var(--accent-emerald);
  color: white;
}

.weight-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.weight-row {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.weight-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.field-key {
  font-size: 12px;
  color: var(--text-muted);
}

.weight-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weight-input {
  width: 80px;
  padding: 10px 14px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 14px;
  text-align: center;
}

.weight-input:focus {
  outline: none;
  border-color: var(--accent-emerald);
}

.weight-unit {
  font-size: 13px;
  color: var(--text-muted);
}

.row-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px 14px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid;
}

.action-btn.edit {
  background: transparent;
  border-color: var(--accent-indigo);
  color: var(--accent-indigo);
}

.action-btn.edit:hover {
  background: rgba(99, 102, 241, 0.1);
}

.action-btn.delete {
  background: transparent;
  border-color: var(--text-muted);
  color: var(--text-secondary);
}

.action-btn.delete:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
  color: #ef4444;
}

.weight-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.total-weight {
  display: flex;
  align-items: center;
  gap: 12px;
}

.total-label {
  font-size: 13px;
  color: var(--text-muted);
}

.total-value {
  font-family: 'DM Serif Display', serif;
  font-size: 18px;
  font-weight: 400;
}

.total-weight.valid .total-value {
  color: var(--accent-emerald);
}

.total-weight.invalid .total-value {
  color: #ef4444;
}

.save-btn {
  padding: 12px 28px;
  background: var(--accent-emerald);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.save-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.save-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.save-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  margin-top: 20px;
}

.save-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.04);
}

.threshold-list,
.poll-row {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 4px;
}

.threshold-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.threshold-info,
.poll-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.threshold-name,
.poll-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.threshold-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.threshold-input-wrap,
.poll-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.threshold-input,
.poll-input {
  width: 80px;
  padding: 10px 14px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 14px;
  text-align: center;
}

.threshold-input:focus,
.poll-input:focus {
  outline: none;
  border-color: var(--accent-emerald);
}

.threshold-unit,
.poll-unit {
  font-size: 13px;
  color: var(--text-muted);
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
}

.dialog {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  width: 420px;
  max-width: 90vw;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.dialog-header h3 {
  font-family: 'DM Serif Display', serif;
  font-size: 18px;
  font-weight: 400;
}

.dialog-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 18px;
}

.dialog-close:hover {
  color: var(--text-primary);
}

.dialog-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 12px 14px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 14px;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--accent-emerald);
}

.form-select {
  cursor: pointer;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

.btn-cancel {
  padding: 10px 20px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
}

.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.04);
}

.btn-confirm {
  padding: 10px 20px;
  background: var(--accent-emerald);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.btn-confirm:hover {
  opacity: 0.9;
}
</style>