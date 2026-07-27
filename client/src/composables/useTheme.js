import { ref, watchEffect } from 'vue'

// Load saved theme from localStorage, default to 'light'
const savedTheme = localStorage.getItem('app-theme') || 'light'
const currentTheme = ref(savedTheme)

// Keep <html data-theme="..."> and localStorage in sync with currentTheme.
// data-theme lives on <html> (not `.app`) so teleported modals, which render
// as siblings of `.app`, still inherit the themed CSS variables.
watchEffect(() => {
  document.documentElement.setAttribute('data-theme', currentTheme.value)
  localStorage.setItem('app-theme', currentTheme.value)
})

export function useTheme() {
  const toggleTheme = () => {
    currentTheme.value = currentTheme.value === 'light' ? 'retro' : 'light'
  }

  return {
    currentTheme,
    toggleTheme
  }
}
