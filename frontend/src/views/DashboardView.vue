<template>
  <div v-if="loading" class="text-slate-500">加载中…</div>
  <div v-else class="space-y-6">
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="s in statCards" :key="s.label" class="card p-5">
        <div class="text-sm text-slate-500">{{ s.label }}</div>
        <div class="mt-2 text-3xl font-bold text-slate-900">{{ s.value }}</div>
      </div>
    </div>

    <p v-if="stats?.workspace_name" class="text-sm text-slate-500">
      当前团队空间：<strong>{{ stats.workspace_name }}</strong>（{{ stats.workspace_members }} 名成员共享数据）
    </p>

    <div class="grid gap-6 lg:grid-cols-2">
      <div class="card p-6">
        <h2 class="font-semibold text-slate-900">快速开始</h2>
        <ul class="mt-4 space-y-3 text-sm text-slate-600">
          <li>1. 在「团队空间」邀请成员，同空间共享已购账号</li>
          <li>2. 在「账号市场」为当前空间购买账号</li>
          <li>2. 在「我的账号」配置人设与 Prompt</li>
          <li>3. 为每个账号设置最多 3 次/天的定时任务（每次 30 分钟）</li>
          <li>4. 使用「批量任务」让多账号同时执行同一任务</li>
        </ul>
        <RouterLink to="/market" class="btn-primary mt-5 inline-flex">去账号市场</RouterLink>
      </div>
      <div class="card p-6">
        <h2 class="font-semibold text-slate-900">环境说明</h2>
        <p class="mt-3 text-sm leading-relaxed text-slate-600">
          当前为 <strong>测试环境</strong>（SpreadFleet / 传播舰队），数据库 schema：<code class="rounded bg-slate-100 px-1">agent_ops_test</code>
          schema。Tactile Agent 执行接口尚未接入，执行日志为演示数据。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, type DashboardStats } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const stats = ref<DashboardStats | null>(null)
const loading = ref(true)

const statCards = computed(() => [
  { label: '我的账号', value: stats.value?.total_accounts_owned ?? 0 },
  { label: '市场可购', value: stats.value?.available_market ?? 0 },
  { label: '活跃定时', value: stats.value?.active_schedules ?? 0 },
  { label: '批量任务', value: stats.value?.batch_tasks ?? 0 },
])

onMounted(async () => {
  if (!auth.token) return
  stats.value = await api.dashboard(auth.token)
  loading.value = false
})
</script>
