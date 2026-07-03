<script lang="ts" setup>
import {
  Combobox,
  ComboboxButton,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from '@headlessui/vue';
import { Down, Up } from '@icon-park/vue-next';
import { isObject, isString } from 'radash';
import type { SelectItem } from '#/components';

const props = withDefaults(
  defineProps<{
    modelValue?: SelectItem | string;
    items: Array<SelectItem | string>;
    editable?: boolean;
  }>(),
  {
    editable: false,
  }
);

const emit = defineEmits(['update:modelValue']);

const selected = ref<SelectItem | string>(
  props.modelValue || (props.items?.[0] ?? '')
);

const query = ref('');

const otherItems = computed(() => {
  return (
    props.items.filter((e) => {
      if (isString(e) && isString(selected.value)) {
        return e !== selected.value;
      } else if (isObject(e) && isObject(selected.value)) {
        return e.id !== selected.value.id;
      } else {
        return false;
      }
    }) ?? []
  );
});

const filteredItems = computed(() => {
  if (query.value === '') {
    return props.items;
  }
  return props.items.filter((item) => {
    const label = isString(item) ? item : item.label ?? item.value;
    return label.toLowerCase().includes(query.value.toLowerCase());
  });
});

/** 当前输入是否匹配了已存在的选项（用于决定是否显示"创建"项） */
const queryMatched = computed(() => {
  if (!query.value) return true;
  return props.items.some((item) => {
    const label = isString(item) ? item : item.label ?? item.value;
    return label.toLowerCase() === query.value.toLowerCase();
  });
});

const label = computed(() => {
  if (isString(selected.value)) {
    return selected.value;
  } else {
    return selected.value.label ?? selected.value.value;
  }
});

function getLabel(item: SelectItem | string) {
  if (isString(item)) {
    return item;
  } else {
    return item.label ?? item.value;
  }
}

function getDisabled(item: SelectItem | string) {
  return isString(item) ? false : item.disabled;
}

watch(selected, (val) => {
  emit('update:modelValue', val);
});
</script>

<template>
  <Combobox v-if="editable" v-slot="{ open }" v-model="selected">
    <div class="select-wrapper editable-select-wrapper">
      <ComboboxInput
        class="select-input"
        :display-value="(val: any) => (isString(val) ? val : '')"
        @change="query = $event.target.value"
        placeholder="gpt-4o"
      />
      <ComboboxButton class="select-button">
        <div :class="[{ hidden: !open }]"><Up :size="14" /></div>
        <div :class="[{ hidden: open }]"><Down :size="14" /></div>
      </ComboboxButton>

      <ComboboxOptions class="select-options">
        <div class="select-options-inner">
          <div class="select-options-list">
            <!-- 当输入的自定义文本未匹配任何选项时，显示"创建"条目 -->
            <ComboboxOption
              v-if="query && !queryMatched"
              :value="query"
            >
              <div class="select-option select-option--create">
                使用 "{{ query }}"
              </div>
            </ComboboxOption>
            <ComboboxOption
              v-for="item in filteredItems"
              v-slot="{ active }"
              :key="isString(item) ? item : item.id"
              :value="item"
              :disabled="getDisabled(item)"
            >
              <div
                class="select-option"
                :class="[
                  active && 'select-option--active',
                  getDisabled(item) && 'select-option--disabled',
                ]"
              >
                {{ getLabel(item) }}
              </div>
            </ComboboxOption>
          </div>
        </div>
      </ComboboxOptions>
    </div>
  </Combobox>

  <Listbox v-else v-slot="{ open }" v-model="selected">
    <div class="select-wrapper">
      <ListboxButton class="select-button">
        <div class="select-value">{{ label }}</div>
        <div :class="[{ hidden: open }]">
          <Down :size="14" />
        </div>
      </ListboxButton>

      <ListboxOptions class="select-options">
        <div class="select-options-inner">
          <div class="select-options-list">
            <ListboxOption
              v-for="item in otherItems"
              v-slot="{ active }"
              :key="isString(item) ? item : item.id"
              :value="item"
              :disabled="getDisabled(item)"
            >
              <div
                class="select-option"
                :class="[
                  active && 'select-option--active',
                  getDisabled(item) && 'select-option--disabled',
                ]"
              >
                {{ getLabel(item) }}
              </div>
            </ListboxOption>
          </div>

          <div :class="[{ hidden: !open }]"><Up :size="14" /></div>
        </div>
      </ListboxOptions>
    </div>
  </Listbox>
</template>

<style lang="scss" scoped>
.select-wrapper {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  font-size: 12px;
  padding: 4px 12px;
  transition: border-color var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
  }
}

.editable-select-wrapper {
  flex-direction: row;
  align-items: center;
  padding: 0 0 0 12px;
  gap: 4px;
}

.select-input {
  flex: 1;
  min-width: 120px;
  background: transparent;
  border: none;
  outline: none;
  color: var(--color-text);
  font-size: 12px;
  padding: 4px 0;
}

.select-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text);
  padding: 0;
}

.select-value {
  color: var(--color-text);
}

.select-options {
  margin-top: 8px;
}

.select-options-inner {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.select-options-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.select-option {
  cursor: pointer;
  user-select: none;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast);

  &--active {
    color: var(--color-primary);
  }

  &--disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  &--create {
    color: var(--color-primary);
    font-style: italic;
  }
}
</style>
