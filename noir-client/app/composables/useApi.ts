/*
 * 認証付き HTTP フェッチ composable（FE-02）。設計指示書 § 6 API 仕様。
 * `Authorization: Bearer` を自動付与し、401 はログイン画面へリダイレクトする。
 */
export function useApi() {
  const { authHeader, apiBase, logout } = useAuth()

  async function apiFetch<T>(path: string, opts: Record<string, unknown> = {}): Promise<T> {
    try {
      return await $fetch<T>(`${apiBase}${path}`, {
        ...opts,
        headers: {
          ...authHeader(),
          ...((opts.headers as Record<string, string>) || {}),
        },
      })
    } catch (err) {
      const e = err as { statusCode?: number }
      if (e?.statusCode === 401) {
        logout()
        await navigateTo('/login')
      }
      throw err
    }
  }

  return { apiFetch }
}
