<template>
    <dl>
    </dl>
    <template v-for="command in commands" :key="command.name">
        <dl><code>{{ command.name }}</code></dl>
        <dt v-html="command.description"> </dt>
    </template>
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
