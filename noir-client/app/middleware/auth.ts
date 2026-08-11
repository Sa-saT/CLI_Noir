/*
 * 未ログインガード（FE-01）。保護ページで `definePageMeta({ middleware: 'auth' })` を指定する。
 * `/login` は対象外（各ページの definePageMeta 側で明示的に付ける方式のため、ここでは除外不要）。
 */
export default defineNuxtRouteMiddleware(() => {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated.value) {
    return navigateTo('/login')
  }
})
