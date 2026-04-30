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

    <el-card style="margin-top: 20px;">
      <template #header>数据清洗</template>
      <el-space wrap>
        <el-button type="primary" :loading="cleaning" @click="handleClean">
          立刻增量清洗
        </el-button>
        <el-button type="warning" :loading="fullCleaning" @click="handleFullClean">
          立刻全量清洗
        </el-button>
      </el-space>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { statsApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const stats = ref({})
const trendData = ref([])
const maxCount = ref(1)
const cleaning = ref(false)
const fullCleaning = ref(false)

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

const handleClean = async () => {
  try {
    cleaning.value = true
    const res = await statsApi.triggerClean()
    if (res.data.message) {
      ElMessage.success(res.data.message)
    } else {
      ElMessage.success('清洗完成')
    }
    // Refresh stats
    const statsRes = await statsApi.get()
    stats.value = statsRes.data
  } catch (error) {
    ElMessage.error('清洗失败')
  } finally {
    cleaning.value = false
  }
}

const handleFullClean = async () => {
  try {
    await ElMessageBox.confirm(
      '全量清洗将重新处理所有数据，确定要继续吗？',
      '全量清洗确认',
      { type: 'warning' }
    )
    fullCleaning.value = true
    const res = await statsApi.triggerFullClean()
    if (res.data.message) {
      ElMessage.success(res.data.message)
    } else {
      ElMessage.success('全量清洗完成')
    }
    // Refresh stats
    const statsRes = await statsApi.get()
    stats.value = statsRes.data
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('全量清洗失败')
    }
  } finally {
    fullCleaning.value = false
  }
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