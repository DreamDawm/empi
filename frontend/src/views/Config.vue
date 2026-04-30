<template>
  <div class="config-page">
    <el-card>
      <template #header>字段权重配置</template>
      <el-form label-width="120px">
        <el-form-item v-for="(weight, field) in weights" :key="field" :label="fieldLabels[field]">
          <el-slider v-model="weights[field]" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveWeights">保存权重</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>合并阈值配置</template>
      <el-form label-width="120px">
        <el-form-item label="自动合并阈值">
          <el-input-number v-model="threshold" :min="0" :max="100" />
          <span style="margin-left: 10px;">分（≥此分数自动合并）</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveThreshold">保存阈值</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { configApi } from '../api'
import { ElMessage } from 'element-plus'

const weights = ref({
  identity_card: 30,
  name: 30,
  birthday: 20,
  gender: 5,
  phone: 10,
  address: 5
})

const threshold = ref(85)

const fieldLabels = {
  identity_card: '身份证号码',
  name: '姓名',
  birthday: '生日',
  gender: '性别',
  phone: '电话',
  address: '地址'
}

onMounted(async () => {
  try {
    const [weightsRes, thresholdRes] = await Promise.all([
      configApi.getWeights(),
      configApi.getThreshold()
    ])
    weights.value = weightsRes.data
    threshold.value = thresholdRes.data.threshold
  } catch (error) {
    ElMessage.error('获取配置失败')
  }
})

const saveWeights = async () => {
  try {
    await configApi.updateWeights(weights.value)
    ElMessage.success('权重保存成功')
  } catch (error) {
    ElMessage.error('权重保存失败')
  }
}

const saveThreshold = async () => {
  try {
    await configApi.updateThreshold(threshold.value)
    ElMessage.success('阈值保存成功')
  } catch (error) {
    ElMessage.error('阈值保存失败')
  }
}
</script>