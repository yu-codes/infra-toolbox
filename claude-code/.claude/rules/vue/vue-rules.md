# Vue 3 Rules

## Component Style

- ALWAYS use `<script setup lang="ts">`
- Define props with `defineProps<{...}>()`
- Define emits with `defineEmits<{...}>()`
- Use `ref()`, `computed()`, `watch()` for reactivity
- Never use Options API

## File Structure

```
src/
  components/          # Reusable UI components
    common/            # Shared components (Button, Input, Modal)
    layout/            # Layout components (Header, Sidebar)
  composables/         # Shared logic (useAuth, useFetch)
  views/               # Page-level components
  stores/              # Pinia stores
  router/              # Vue Router config
  types/               # TypeScript type definitions
  utils/               # Pure utility functions
  assets/              # Static assets (images, fonts)
```

## Naming Conventions

- Components: PascalCase (`UserProfile.vue`)
- Composables: camelCase with `use` prefix (`useAuth.ts`)
- Stores: camelCase with `use` prefix and `Store` suffix (`useUserStore.ts`)
- Views: PascalCase with `View` suffix (`DashboardView.vue`)

## State Management

- Use Pinia for global state
- Prefer composables for local shared state
- Keep stores focused — one store per domain
- Use `storeToRefs()` for reactive destructuring

## Styling

- Scoped styles preferred (`<style scoped>`)
- Use CSS variables for theming
- Utility-first CSS (Tailwind) or component-scoped styles
- Never use inline styles for anything other than dynamic values

## Testing

- Use Vitest + @vue/test-utils
- Mount components with realistic props
- Test user interactions, not implementation details
- Use `happy-dom` for faster test execution

## Template

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  title: string
  count?: number
}>()

const emit = defineEmits<{
  update: [value: string]
}>()

const localValue = ref('')
const displayTitle = computed(() => `${props.title} (${props.count ?? 0})`)
</script>

<template>
  <div class="component-name">
    <h2>{{ displayTitle }}</h2>
    <input v-model="localValue" @change="emit('update', localValue)" />
  </div>
</template>

<style scoped>
.component-name {
  /* styles */
}
</style>
```
