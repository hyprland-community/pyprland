<template>
    <dl>
    </dl>
    <ul v-for="command in commands" :key="command.name">
        <li><code>{{ command.name }}</code> <span v-html="command.description" /></li>
    </ul>
</template>

<script>
export default {
    props: {
        commands: {
            type: Array,
            required: true
        }
    }
}
</script>
