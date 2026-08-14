<script setup lang="ts">
import { ref } from 'vue'

// ログイン画面（FE-01）。設計指示書 § 6 `POST /api/auth/login/`。
definePageMeta({ layout: false })

const { login, isAuthenticated } = useAuth()
const router = useRouter()
const route = useRoute()

if (isAuthenticated.value) {
  await navigateTo((route.query.redirect as string) || '/missions')
}

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  if (!username.value || !password.value) return
  loading.value = true
  error.value = ''
  try {
    await login(username.value, password.value)
    const redirect = (route.query.redirect as string) || '/missions'
    await router.push(redirect)
  } catch (err) {
    error.value = authErrorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-screen">
    <form class="login-card" @submit.prevent="onSubmit">
      <p class="tag">CLI_Noir</p>
      <h1>探偵事務所 — 入館認証</h1>
      <p class="lead">バッジ番号（ユーザー名）とパスワードを入力してください。</p>

      <label class="field">
        <span>ユーザー名</span>
        <input
          v-model="username"
          type="text"
          autocomplete="username"
          autocapitalize="off"
          spellcheck="false"
          required
        >
      </label>

      <label class="field">
        <span>パスワード</span>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
        >
      </label>

      <p v-if="error" class="error">{{ error }}</p>

      <NoirButton type="submit" variant="primary" size="lg" :disabled="loading">
        {{ loading ? '認証中…' : '入館する' }}
      </NoirButton>
    </form>
  </div>
</template>

<style scoped>
.login-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(120% 100% at 50% 0%, rgba(99, 102, 241, 0.12), var(--bg-app-deep) 60%);
  padding: var(--space-4);
}
.login-card {
  width: 380px;
  max-width: 100%;
  background: var(--hairline-scan), linear-gradient(180deg, var(--gray-800), var(--gray-900));
  border: 1px solid var(--brass-600);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel), var(--bezel-brass);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.tag {
  margin: 0;
  font-family: var(--font-accent);
  letter-spacing: var(--tracking-hero);
  text-transform: uppercase;
  font-size: var(--text-xs);
  color: var(--brass-400);
}
h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--text-body);
}
.lead {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-muted);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: var(--text-sm);
  color: var(--text-faint);
}
.field input {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  background: var(--gray-900);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  color: var(--text-body);
  outline: none;
}
.field input:focus {
  border-color: var(--accent);
  box-shadow: var(--glow-indigo);
}
.error {
  margin: 0;
  color: var(--term-error);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}
</style>
