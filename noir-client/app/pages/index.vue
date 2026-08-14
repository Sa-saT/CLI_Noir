<script setup lang="ts">
/*
 * ルート `/` はエントリポイントのみ（設計指示書 § 3 のルーティングは /missions 以下）。
 * FE-04: 旧モック evaluator（ローカルスタンドイン実装）はここに置かれていたが、
 * 実バックエンド接続（app/pages/missions/[id].vue + useTerminalSocket）へ完全移行したため撤去。
 */
const { isAuthenticated } = useAuth()
await navigateTo(isAuthenticated.value ? '/missions' : '/login')
</script>

<template>
  <div />
</template>
