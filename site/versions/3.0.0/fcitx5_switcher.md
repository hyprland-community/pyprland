---
---

# fcitx5_switcher

This is a useful tool for CJK input method users.

It can automatically switch fcitx5 input method status based on window class and title.

<details>
<summary>Example</summary>

```toml
[fcitx5_switcher]
active_classes = ["wechat", "QQ", "zoom"]
inactive_classes = [
    "code",
    "kitty",
    "google-chrome",
]
active_titles = []
inactive_titles = []
```

In this example, if the window class is "wechat" or "QQ" or "zoom", the input method will be activated. If the window class is "code" or "kitty" or "google-chrome", the input method will be inactivated.

</details>

## Commands

*No commands available.*


## Configuration

| Option | Description |
|--------|-------------|
| `active_classes` · *list* | Window classes that should activate Fcitx5 |
| `active_titles` · *list* | Window titles that should activate Fcitx5 |
| `inactive_classes` · *list* | Window classes that should deactivate Fcitx5 |
| `inactive_titles` · *list* | Window titles that should deactivate Fcitx5 |


