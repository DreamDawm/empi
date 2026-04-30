<template>
  <div class="pending-page">
    <el-card>
      <template #header>
        <span>待审核列表</span>
        <el-button type="primary" size="small" @click="loadCandidates">刷新</el-button>
      </template>
      <el-table :data="candidates" stripe>
        <el-table-column prop="patient_a.patient_name" label="患者A" />
        <el-table-column prop="patient_b.patient_name" label="患者B" />
        <el-table-column prop="similarity_score" label="相似度">
          <template #default="{ row }">
            <el-tag :type="getScoreType(row.similarity_score)">{{ row.similarity_score }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleMerge(row)">合并</el-button>
            <el-button type="info" size="small" @click="handleIgnore(row)">忽略</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadCandidates"
        style="margin-top: 20px; justify-content: center;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { mergeApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const candidates = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(() => {
  loadCandidates()
})

const loadCandidates = async () => {
  try {
    const res = await mergeApi.listCandidates(page.value, pageSize.value)
    candidates.value = res.data.data || []
    total.value = res.data.total || 0
  } catch (error) {
    ElMessage.error('获取待审核列表失败')
  }
}

const getScoreType = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'info'
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