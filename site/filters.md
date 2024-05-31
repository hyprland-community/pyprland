At the moment there is only one filter, close match of [sed's "s" command](https://www.gnu.org/software/sed/manual/html_node/The-_0022s_0022-Command.html).

The only supported flag is "g"

## Example

```toml
filter = 's/foo/bar/'
filter = 's/.*started (.*)/\1 has started/'
filter = 's#</?div>##g'
```
