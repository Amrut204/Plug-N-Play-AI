<!-- src/lib/AIWidget.svelte (Svelte / SvelteKit) -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let userId: string = 'guest';
  export let userRole: string = 'user';

  let scriptEl: HTMLScriptElement;

  onMount(() => {
    scriptEl = document.createElement('script');
    // Paste your exported Svelte component configuration from Agent Studio below:
    scriptEl.src = 'https://plug-n-play-rag.onrender.com/static/pnp-widget.js';
    scriptEl.setAttribute('data-api-host', 'https://plug-n-play-rag.onrender.com');
    scriptEl.setAttribute('data-agent-id', 'YOUR_AGENT_ID');
    scriptEl.setAttribute('data-title', 'AI Assistant');
    scriptEl.setAttribute('data-user-id', userId);
    scriptEl.setAttribute('data-user-role', userRole);
    scriptEl.setAttribute('data-theme', 'dark');
    scriptEl.async = true;
    document.body.appendChild(scriptEl);
  });

  onDestroy(() => {
    if (scriptEl && document.body.contains(scriptEl)) {
      document.body.removeChild(scriptEl);
    }
    document.getElementById('pnp-widget-container')?.remove();
    document.getElementById('pnp-widget-trigger')?.remove();
  });
</script>