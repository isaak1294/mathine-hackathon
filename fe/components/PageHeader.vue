<template>
  <header>
    <AppNavbar :items="navItems">

    </AppNavbar>
  </header>
</template>

<script setup lang="ts">
import AppNavbar from './Navbar.vue'

const navItems = [
  { label: 'Submission', href: '/submission' },
  { label: 'Kanban', href: '/kanban' },
  { label: 'Calendar', href: '/calendar' },
  { label: 'Braindump', href: '/braindump' }
]
</script>
