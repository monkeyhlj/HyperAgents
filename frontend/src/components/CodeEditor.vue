<template>
  <div class="code-editor-shell">
    <Codemirror
      :model-value="modelValue"
      :extensions="editorExtensions"
      :placeholder="placeholder"
      :style="{ minHeight }"
      basic
      @update:model-value="emit('update:modelValue', $event)"
    />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { Codemirror } from "vue-codemirror";
import { json as jsonLanguage } from "@codemirror/lang-json";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView, placeholder as placeholderExtension } from "@codemirror/view";

const props = defineProps({
  modelValue: {
    type: String,
    default: ""
  },
  language: {
    type: String,
    default: "text"
  },
  placeholder: {
    type: String,
    default: ""
  },
  minHeight: {
    type: String,
    default: "220px"
  }
});

const emit = defineEmits(["update:modelValue"]);

const editorExtensions = computed(() => {
  const extensions = [EditorView.lineWrapping, oneDark];
  if (props.placeholder) {
    extensions.push(placeholderExtension(props.placeholder));
  }
  if (props.language === "python") {
    extensions.push(python());
  } else if (props.language === "json") {
    extensions.push(jsonLanguage());
  }
  return extensions;
});
</script>

<style scoped>
.code-editor-shell {
  border: 1px solid #d7e3ef;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.code-editor-shell :deep(.cm-editor) {
  font-size: 13px;
  font-family: "Consolas", "SFMono-Regular", "Cascadia Code", monospace;
}

.code-editor-shell :deep(.cm-scroller) {
  overflow: auto;
}

.code-editor-shell :deep(.cm-focused) {
  outline: none;
}
</style>