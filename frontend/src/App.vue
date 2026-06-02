<template>
  <div class="layout">
    <aside class="sidebar">
      <h1>HyperAgents</h1>
      <p class="subtitle">AgentOS Workspace</p>
      <nav>
        <RouterLink to="/">Dashboard</RouterLink>
        <RouterLink to="/projects">Projects</RouterLink>
        <RouterLink to="/resources">Resources</RouterLink>
        <RouterLink to="/workbench">Workbench</RouterLink>
      </nav>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from "vue-router";
</script>
