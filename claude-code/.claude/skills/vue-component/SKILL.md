# Skill: vue-component

Scaffold a Vue 3 component using the Composition API.

## Steps

1. Identify component purpose and props
2. Write the `<script setup>` block:
   - Define props with `defineProps`
   - Define emits with `defineEmits`
   - Use `ref` / `computed` / `watch` as needed
3. Write the `<template>` block (semantic HTML)
4. Write scoped `<style>` if needed

## Template

```vue
<script setup lang="ts">
const props = defineProps<{
  label: string
  value?: string
}>()

const emit = defineEmits<{
  (e: 'change', value: string): void
}>()
</script>

<template>
  <div class="component-name">
    <!-- content -->
  </div>
</template>

<style scoped>
</style>
```

## Rules

- Always use `<script setup>` — never Options API
- Type props and emits explicitly
- One component per file
- No inline styles — use scoped CSS or utility classes
