<!-- src/components/AIWidget.vue (Vue 3 / Nuxt 3 with TypeScript) -->
<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';

const props = defineProps<{
  userId?: string;
  userRole?: string;
}>();

let scriptEl: HTMLScriptElement | null = null;

onMounted(() => {
  scriptEl = document.createElement('script');
  // Paste your exported Vue/Nuxt component configuration from Agent Studio below:
  scriptEl.src = 'https://plug-n-play-rag.onrender.com/static/pnp-widget.js';
  scriptEl.setAttribute('data-api-host', 'https://plug-n-play-rag.onrender.com');
  scriptEl.setAttribute('data-agent-id', 'YOUR_AGENT_ID');
  scriptEl.setAttribute('data-title', 'AI Assistant');
  if (props.userId) scriptEl.setAttribute('data-user-id', props.userId);
  if (props.userRole) scriptEl.setAttribute('data-user-role', props.userRole);
  scriptEl.setAttribute('data-theme', 'dark');
  scriptEl.async = true;
  document.body.appendChild(scriptEl);
});

onUnmounted(() => {
  if (scriptEl && document.body.contains(scriptEl)) {
    document.body.removeChild(scriptEl);
  }
  document.getElementById('pnp-widget-container')?.remove();
  document.getElementById('pnp-widget-trigger')?.remove();
});
</script>

<template></template>