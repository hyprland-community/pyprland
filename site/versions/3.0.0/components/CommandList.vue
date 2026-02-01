<template>
  <ul v-for="command in commands" :key="command.name">
    <li>
      <code v-html="command.name.replace(/[ ]*$/, '').replace(/ +/g, '&ensp;')" />&ensp;
      <span v-html="renderDescription(command.description)" />
    </li>
  </ul>
</template>

<script>
import { renderDescription } from './configHelpers.js'

export default {
  props: {
    commands: {
      type: Array,
      required: true
    }
  },
  methods: {
    renderDescription
  }
}
</script>
