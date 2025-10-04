<template>
  <div class="min-h-screen flex flex-col">
    <PageHeader />
    <main class="flex-1">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
/* Using Tailwind classes instead of SCSS for consistency */
</style>