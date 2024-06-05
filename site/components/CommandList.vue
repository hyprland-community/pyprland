<template>
    <dl>
    </dl>
    <ul v-for="command in commands" :key="command.name">
        <li><code v-html="command.name.replace(/ /g, '&ensp; ')" /> <span v-html="command.description" /></li>
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
