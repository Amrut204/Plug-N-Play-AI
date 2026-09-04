<script setup lang="ts">
import { ref } from 'vue';
import AIWidget from './components/AIWidget.vue';

const patientId = ref('pt_metro_8841');
const selectedDepartment = ref('Cardiology');
</script>

<template>
  <div style="max-width: 1100px; margin: 0 auto; padding: 40px 24px;">
    <header style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 24px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 36px;">
      <div style="font-size: 20px; font-weight: 800; display: flex; align-items: center; gap: 8px;">
        🏥 MetroHealth Patient Portal
      </div>
      <div style="font-size: 13px; color: #a1a1aa;">
        Patient ID: {{ patientId }}
      </div>
    </header>

    <main>
      <div style="background: #121215; border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 36px; margin-bottom: 32px;">
        <h1 style="font-size: 28px; font-weight: 800; margin-bottom: 12px;">Diagnostic Lab &amp; Follow-up Consultations</h1>
        <p style="color: #a1a1aa; font-size: 15px; margin: 0;">
          Schedule outpatient appointments, check fasting preparation guidelines, and view digital lab reports.
        </p>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
        <div style="background: #121215; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 24px;">
          <div style="font-size: 12px; color: #4ade80; font-weight: 700; text-transform: uppercase;">Upcoming Appointment</div>
          <div style="font-size: 18px; font-weight: 700; color: #ffffff; margin: 8px 0;">Routine Cardiology Review</div>
          <div style="font-size: 13px; color: #a1a1aa;">Dr. Sarah Jenkins &bull; Thursday at 10:30 AM</div>
        </div>

        <div style="background: #121215; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 24px;">
          <div style="font-size: 12px; color: #38bdf8; font-weight: 700; text-transform: uppercase;">Insurance Coverage</div>
          <div style="font-size: 18px; font-weight: 700; color: #ffffff; margin: 8px 0;">BlueCross BlueShield</div>
          <div style="font-size: 13px; color: #22c55e;">Active &bull; Standard In-Network Co-Pay</div>
        </div>
      </div>
    </main>

    <!-- ================================================================= -->
    <!-- 🔌 PLUG-N-PLAY AI WIDGET COMPONENT (VUE 3 / NUXT 3 TARGET)         -->
    <!-- ================================================================= -->
    <AIWidget :userId="patientId" userRole="user" />
  </div>
</template>
