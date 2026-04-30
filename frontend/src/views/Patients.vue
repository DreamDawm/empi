<template>
  <div class="patients-page">
    <el-card>
      <template #header>患者查询</template>
      <el-form inline>
        <el-form-item label="患者ID">
          <el-input v-model="searchId" placeholder="输入患者ID" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="searchPatient">查询</el-button>
        </el-form-item>
      </el-form>

      <div v-if="patient" style="margin-top: 20px;">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="患者ID">{{ patient.patient_id }}</el-descriptions-item>
          <el-descriptions-item label="患者姓名">{{ patient.patient_name }}</el-descriptions-item>
          <el-descriptions-item label="主索引ID">{{ patient.master_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="patient.status === 'NORMAL' ? 'success' : 'warning'">
              {{ patient.status === 'NORMAL' ? '正常' : '已合并' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="masterInfo" style="margin-top: 20px;">
          <h4>主索引信息</h4>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="主索引ID">{{ masterInfo.master_id }}</el-descriptions-item>
            <el-descriptions-item label="主患者">{{ masterInfo.primary_patient?.patient_name }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="masterInfo.merged_patients?.length" style="margin-top: 10px;">
            <h4>已合并患者</h4>
            <el-tag v-for="p in masterInfo.merged_patients" :key="p.patient_id" style="margin-right: 10px;">
              {{ p.patient_name }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { patientsApi } from '../api'
import { ElMessage } from 'element-plus'

const searchId = ref('')
const patient = ref(null)
const masterInfo = ref(null)

const searchPatient = async () => {
  if (!searchId.value) {
    ElMessage.warning('请输入患者ID')
    return
  }
  try {
    patient.value = await patientsApi.get(searchId.value)
    const masterRes = await patientsApi.getMaster(searchId.value)
    masterInfo.value = masterRes.data
  } catch (error) {
    ElMessage.error('患者不存在')
    patient.value = null
    masterInfo.value = null
  }
}
</script>