<script setup lang="ts">
import AppLogo from '@/app/layouts/components/AppLogo.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
    <div class="mb-8">
      <AppLogo />
    </div>
    <main class="w-full max-w-sm">
      <RouterView />
    </main>
  </div>
</template>
