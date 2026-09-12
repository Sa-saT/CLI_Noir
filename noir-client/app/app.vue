<script setup lang="ts">
/*
 * 「常時ターミナル」の接続ライフサイクル（Phase E: FE3-01/FE3-02。docs/DESIGN.md § 7）。
 * ログイン状態にひもづけて WS 接続を張る/切るのはここだけ。Mission ページ側からは
 * connect/disconnect を呼ばない（表示切替専用。app/pages/missions/[id].vue 参照）。
 */
const { isAuthenticated } = useAuth()
const socket = useTerminalSocket()

watch(isAuthenticated, (loggedIn) => {
  if (import.meta.server) return
  if (loggedIn) socket.connect()
  else socket.disconnect()
}, { immediate: true })
</script>

<template>
  <div>
    <NuxtRouteAnnouncer />
    <NuxtPage />
  </div>
</template>
