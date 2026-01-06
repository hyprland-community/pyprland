<template>
  <ul v-for="command in commands" :key="command.name">
    <li>
      <code v-html="command.name.replace(/[ ]*$/, '').replace(/ /g, '&ensp;')" />
      <span v-html="renderDescription(command.description)" />
    </li>
  </ul>
</template>

<script>
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ html: true, linkify: true })

export default {
  props: {
    commands: {
      type: Array,
      required: true
    }
  },
  methods: {
    renderDescription(text) {
      return md.renderInline(text)
    }
  }
}
</script>
