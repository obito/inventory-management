<template>
  <button
    class="theme-toggle"
    type="button"
    role="switch"
    :aria-checked="currentTheme === 'retro'"
    :aria-label="`Switch to ${currentTheme === 'retro' ? 'Light' : 'Retro'} theme`"
    @click="toggleTheme"
  >
    <span class="theme-toggle-option" :class="{ active: currentTheme === 'light' }">LIGHT</span>
    <span class="theme-toggle-option" :class="{ active: currentTheme === 'retro' }">RETRO</span>
  </button>
</template>

<script setup>
import { useTheme } from '../composables/useTheme'

const { currentTheme, toggleTheme } = useTheme()
</script>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  padding: 0.25rem;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  cursor: pointer;
  font-family: inherit;
}

.theme-toggle-option {
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-badge);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.025em;
  color: var(--color-panel-text-secondary);
  transition: all 0.2s ease;
}

.theme-toggle-option.active {
  background: var(--color-panel);
  color: var(--color-accent);
  box-shadow: var(--shadow-card);
}
</style>
