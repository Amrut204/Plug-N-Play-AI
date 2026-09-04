import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AIWidgetComponent } from './components/ai-widget.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, AIWidgetComponent],
  templateUrl: './app.component.html',
  styleUrls: []
})
export class AppComponent {
  title = 'Apex Institute Student ERP';
}
