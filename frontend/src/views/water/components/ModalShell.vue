<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div class="modal-card" :style="width ? { width } : undefined">
      <header class="modal-head">
        <h3>{{ title }}</h3>
        <button class="link" type="button" @click="$emit('close')">关闭</button>
      </header>
      <div class="modal-body">
        <slot />
      </div>
      <footer v-if="$slots.footer" class="modal-foot">
        <slot name="footer" />
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; width?: string }>()
defineEmits<{ (e: 'close'): void }>()
</script>
