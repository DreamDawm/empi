<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <template #header>患者总数</template>
          <div class="stat-value">{{ stats.total || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>已合并</template>
          <div class="stat-value">{{ stats.merged || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>待审核</template>
          <div class="stat-value">{{ stats.pending || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>合并率</template>
          <div class="stat-value">{{ stats.merge_rate || 0 }}%</div>
        </el-card>
      </el-col>
    </el-row>
    <el-card style="margin-top: 20px;">
      <template #header>合并趋势（近7天）</template>
      <div v-if="trendData.length">
        <div v-for="item in trendData" :key="item.date" class="trend-item">
          <span>{{ item.date }}</span>
          <el-progress :percentage="getMaxPercentage(item.count)" :show-text="false" />
          <span>{{ item.count }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无数据" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { statsApi } from '../api'
import { ElMessage } from 'element-plus'

const stats = ref({})
const trendData = ref([])
const maxCount = ref(1)

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
    ElMessage.error('获取统计数据失败')
  }
})

const getMaxPercentage = (count) => {
  return Math.round((count / maxCount.value) * 100)
}
</script>

<style scoped>
.stat-value {
  font-size: 2rem;
  font-weight: bold;
  text-align: center;
  padding: 1rem 0;
}
.trend-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.trend-item span:first-child {
  width: 100px;
}
.trend-item span:last-child {
  width: 50px;
  text-align: right;
}
</style>