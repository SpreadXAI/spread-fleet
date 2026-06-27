<template>
  <div>
    <h2 class="mb-4 text-lg font-semibold">全部团队空间</h2>
    <div v-if="loading" class="text-slate-500">加载中…</div>
    <div v-else class="space-y-3">
      <div
        v-for="w in workspaces"
        :key="w.id"
        class="card flex flex-wrap items-center justify-between gap-4 p-4"
      >
        <div>
          <div class="font-medium">{{ w.name }}</div>
          <div class="mt-1 text-sm text-slate-500">
            ID {{ w.id }} · {{ w.member_count }} 成员 · {{ w.account_count }} 账号 ·
            套餐 {{ w.plan?.name ?? '无' }}
          </div>
        </div>
        <RouterLink :to="`/admin/workspaces/${w.id}`" class="btn-secondary">查看详情</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, type Workspace } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const workspaces = ref<Workspace[]>([])
const loading = ref(true)

onMounted(async () => {
  if (!auth.token) return
  workspaces.value = await api.adminWorkspaces(auth.token)
  loading.value = false
})
</script>
