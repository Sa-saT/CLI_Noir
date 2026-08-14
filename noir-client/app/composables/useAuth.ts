import { computed, ref } from 'vue'

/*
 * 認証 composable（FE-01）。設計指示書 § 2 認証 / § 6 API。
 * access token を localStorage に保存する（SPA・§ 2 で SSR 非採用のため単純な方式で可）。
 * WebSocket 認証（§ 7）はこの token を最初の `auth` フレームで渡す。
 */

const TOKEN_KEY = 'clinoir_access_token'
const REFRESH_KEY = 'clinoir_refresh_token'

// モジュールスコープの単一 state（SPA なのでページ間で共有すれば十分）。
const accessToken = ref<string | null>(null)
let hydrated = false

function hydrate() {
  if (hydrated || import.meta.server) return
  hydrated = true
  accessToken.value = localStorage.getItem(TOKEN_KEY)
}

interface LoginResponse {
  access_token: string
  refresh_token?: string | null
  token_type: string
}

export function useAuth() {
  hydrate()
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase as string

  const isAuthenticated = computed(() => !!accessToken.value)

  async function login(username: string, password: string): Promise<void> {
    const res = await $fetch<LoginResponse>(`${apiBase}/api/auth/login/`, {
      method: 'POST',
      body: { username, password },
    })
    accessToken.value = res.access_token
    if (!import.meta.server) {
      localStorage.setItem(TOKEN_KEY, res.access_token)
      if (res.refresh_token) localStorage.setItem(REFRESH_KEY, res.refresh_token)
    }
  }

  function logout(): void {
    accessToken.value = null
    if (!import.meta.server) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
    }
  }

  function getToken(): string | null {
    return accessToken.value
  }

  function authHeader(): Record<string, string> {
    return accessToken.value ? { Authorization: `Bearer ${accessToken.value}` } : {}
  }

  return { isAuthenticated, login, logout, getToken, authHeader, apiBase }
}

/** ログイン API のエラーメッセージ抽出（設計指示書 § 12 の文言をそのまま出す）。 */
export function authErrorMessage(err: unknown): string {
  const e = err as { data?: { detail?: string }, statusCode?: number }
  if (e?.data?.detail) return e.data.detail
  if (e?.statusCode === 401) return 'Error: unauthorized'
  return 'Error: network'
}
