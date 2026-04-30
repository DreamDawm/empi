<template>
  <div class="config-page">
    <el-card>
      <template #header>
        <span>字段权重配置</span>
        <el-button type="success" size="small" @click="addField" style="margin-left: 10px;">
          添加字段
        </el-button>
      </template>
      <el-form label-width="120px">
        <el-form-item v-for="(item, index) in weights" :key="index" :label="item.display_name || item.field_name">
          <el-input-number v-model="item.weight" :min="0" :max="100" />
          <el-button type="primary" size="small" @click="editField(index)" style="margin-left: 10px;">
            编辑
          </el-button>
          <el-button type="danger" size="small" @click="removeField(index)" style="margin-left: 10px;">
            删除
          </el-button>
        </el-form-item>

        <el-form-item label="权重总分">
          <el-tag :type="totalWeight === 100 ? 'success' : 'danger'" size="large">
            {{ totalWeight }} / 100
          </el-tag>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :disabled="totalWeight !== 100" @click="saveWeights">
            保存权重
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>合并阈值配置</template>
      <el-form label-width="140px">
        <el-form-item label="自动合并阈值">
          <el-input-number v-model="threshold" :min="0" :max="100" />
          <span style="margin-left: 10px;">分（≥此分数自动合并）</span>
        </el-form-item>
        <el-form-item label="待审核显示阈值">
          <el-input-number v-model="pendingThreshold" :min="0" :max="100" />
          <span style="margin-left: 10px;">分（<此分数不显示在待审核列表）</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveThreshold">保存阈值</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>ETL轮询配置</template>
      <el-form label-width="140px">
        <el-form-item label="轮询间隔">
          <el-input-number v-model="pollInterval" :min="1" :max="24" :step="1" />
          <span style="margin-left: 10px;">小时</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="savePollInterval">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="showAddDialog" title="添加字段" width="400px">
      <el-form>
        <el-form-item label="选择字段">
          <el-select v-model="newField.field_name" placeholder="请选择字段">
            <el-option
              v-for="field in availableFields"
              :key="field"
              :label="field"
              :value="field"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="newField.display_name" placeholder="请输入显示名称" />
        </el-form-item>
        <el-form-item label="权重">
          <el-input-number v-model="newField.weight" :min="0" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddField">确定</el-button>
      </template>
    </el-dialog>
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
const newField = ref({ field_name: '', display_name: '', weight: 0 })

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
    ElMessage.error('获取配置失败')
  }
})

const addField = () => {
  newField.value = { field_name: '', display_name: '', weight: 0 }
  showAddDialog.value = true
}

const confirmAddField = () => {
  if (!newField.value.field_name) {
    ElMessage.warning('请选择字段')
    return
  }
  if (!newField.value.display_name) {
    ElMessage.warning('请输入显示名称')
    return
  }
  weights.value.push({ ...newField.value })
  showAddDialog.value = false
}

const removeField = (index) => {
  weights.value.splice(index, 1)
}

const editField = (index) => {
  ElMessage.info('编辑功能待实现')
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
