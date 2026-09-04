// src/app/components/ai-widget.component.ts (Angular 14/15/16/17+)
import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Component({
  selector: 'app-ai-widget',
  template: '',
  standalone: true
})
export class AIWidgetComponent implements OnInit, OnDestroy {
  private scriptElement?: HTMLScriptElement;

  constructor(@Inject(PLATFORM_ID) private platformId: Object) {}

  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.scriptElement = document.createElement('script');
      // Paste your exported Angular component configuration from Agent Studio below:
      this.scriptElement.src = 'https://plug-n-play-rag.onrender.com/static/pnp-widget.js';
      this.scriptElement.setAttribute('data-api-host', 'https://plug-n-play-rag.onrender.com');
      this.scriptElement.setAttribute('data-agent-id', 'YOUR_AGENT_ID');
      this.scriptElement.setAttribute('data-title', 'Campus AI Advisor');
      this.scriptElement.setAttribute('data-theme', 'dark');
      this.scriptElement.async = true;
      document.body.appendChild(this.scriptElement);
    }
  }

  ngOnDestroy(): void {
    if (this.scriptElement) {
      document.body.removeChild(this.scriptElement);
      document.getElementById('pnp-widget-container')?.remove();
      document.getElementById('pnp-widget-trigger')?.remove();
    }
  }
}