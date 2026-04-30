<template>
  <div class="merged-page">
    <el-card>
      <template #header>合并历史</template>
      <el-table :data="history" stripe>
        <el-table-column prop="person_id_a" label="患者A ID" />
        <el-table-column prop="person_id_b" label="患者B ID" />
        <el-table-column prop="master_id" label="主索引ID" />
        <el-table-column prop="merge_type" label="合并类型">
          <template #default="{ row }">
            <el-tag :type="row.merge_type === 'AUTO' ? 'success' : 'primary'">
              {{ row.merge_type === 'AUTO' ? '自动' : '人工' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="similarity_score" label="相似度" />
        <el-table-column prop="merge_time" label="合并时间" />
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadHistory"
        style="margin-top: 20px; justify-content: center;"
      />
    </el-card>
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