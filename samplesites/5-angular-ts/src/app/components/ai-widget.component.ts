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
      this.scriptElement.src = 'http://127.0.0.1:8000/static/pnp-widget.js';
      this.scriptElement.setAttribute('data-api-host', 'http://127.0.0.1:8000');
      this.scriptElement.setAttribute('data-agent-id', '9b7f7f22-a73c-472a-8f14-0b97c6e0e63d');
      this.scriptElement.setAttribute('data-title', 'customersupport');
      this.scriptElement.setAttribute('data-primary-color', '#09090b');
      this.scriptElement.setAttribute('data-accent-color', '#318c52');
      this.scriptElement.setAttribute('data-bg-color', '#09090b');
      this.scriptElement.setAttribute('data-header-bg', '#121215');
      this.scriptElement.setAttribute('data-text-color', '#f8fafc');
      this.scriptElement.setAttribute('data-user-bubble', '#ffffff');
      this.scriptElement.setAttribute('data-position', 'bottom-right');
      this.scriptElement.setAttribute('data-widget-size', 'medium');
      this.scriptElement.setAttribute('data-btn-shape', 'circle');
      this.scriptElement.setAttribute('data-border-radius', '24');
      this.scriptElement.setAttribute('data-theme', 'dark');
      this.scriptElement.setAttribute('data-welcome', 'Hello! I am your AI Assistant. Ask me anything or tap the mic to speak:');
      this.scriptElement.setAttribute('data-show-branding', 'true');
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