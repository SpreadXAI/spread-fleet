<template>
  <div class="card max-w-lg space-y-6 p-6">
    <div>
      <label for="profile-nickname" class="mb-1 block text-sm font-medium text-slate-700">昵称</label>
      <input
        id="profile-nickname"
        v-model="nickname"
        class="input"
        type="text"
        maxlength="128"
        placeholder="设置一个显示昵称（可选）"
      />
      <p class="mt-1 text-xs text-slate-500">侧边栏和页面顶部会显示昵称；未设置则显示邮箱。</p>
    </div>
    <button class="btn-primary" :disabled="saving" @click="save">
      {{ saving ? '保存中…' : '保存昵称' }}
    </button>
    <p v-if="msg" class="text-sm text-green-600">{{ msg }}</p>

    <dl class="space-y-4 border-t border-slate-100 pt-6 text-sm">
      <div class="flex justify-between border-b border-slate-100 pb-3">
        <dt class="text-slate-500">邮箱</dt>
        <dd class="font-medium">{{ auth.user?.email }}</dd>
      </div>
      <div class="flex justify-between border-b border-slate-100 pb-3">
        <dt class="text-slate-500">用户 ID</dt>
        <dd class="font-medium">{{ auth.user?.id }}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-slate-500">注册时间</dt>
        <dd class="font-medium">{{ auth.user ? formatTime(auth.user.created_at) : '—' }}</dd>
      </div>
    </dl>

    <div v-if="auth.user?.is_admin" class="border-t border-slate-100 pt-6">
      <a
        href="/spreadfleet/admin"
        target="_blank"
        rel="noopener noreferrer"
        class="btn-secondary inline-flex w-full justify-center"
      >
        打开管理台 ↗
      </a>
      <p class="mt-2 text-xs text-slate-500">在新标签页中打开平台管理后台</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const nickname = ref('')
const saving = ref(false)
const msg = ref('')

onMounted(() => {
  nickname.value = auth.user?.display_name ?? ''
})

async function save() {
  saving.value = true
  msg.value = ''
  try {
    await auth.updateProfile(nickname.value)
    msg.value = '已保存'
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '保存失败'
  } finally {
    saving.value = false
  }
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}
</script>
