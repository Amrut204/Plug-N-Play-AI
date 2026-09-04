<!-- src/lib/AIWidget.svelte (Svelte / SvelteKit) -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let userId: string = 'guest';
  export let userRole: string = 'user';

  let scriptEl: HTMLScriptElement;

  onMount(() => {
    scriptEl = document.createElement('script');
    scriptEl.src = 'http://127.0.0.1:8000/static/pnp-widget.js';
    scriptEl.setAttribute('data-api-host', 'http://127.0.0.1:8000');
    scriptEl.setAttribute('data-agent-id', '9b7f7f22-a73c-472a-8f14-0b97c6e0e63d');
    scriptEl.setAttribute('data-title', 'customersupport');
    scriptEl.setAttribute('data-user-id', userId);
    scriptEl.setAttribute('data-user-role', userRole);
    scriptEl.setAttribute('data-primary-color', '#09090b');
    scriptEl.setAttribute('data-accent-color', '#318c52');
    scriptEl.setAttribute('data-bg-color', '#09090b');
    scriptEl.setAttribute('data-header-bg', '#121215');
    scriptEl.setAttribute('data-text-color', '#f8fafc');
    scriptEl.setAttribute('data-user-bubble', '#ffffff');
    scriptEl.setAttribute('data-position', 'bottom-right');
    scriptEl.setAttribute('data-widget-size', 'medium');
    scriptEl.setAttribute('data-btn-shape', 'circle');
    scriptEl.setAttribute('data-border-radius', '24');
    scriptEl.setAttribute('data-theme', 'dark');
    scriptEl.setAttribute('data-welcome', 'Hello! I am your AI Assistant. Ask me anything or tap the mic to speak:');
    scriptEl.setAttribute('data-show-branding', 'true');
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