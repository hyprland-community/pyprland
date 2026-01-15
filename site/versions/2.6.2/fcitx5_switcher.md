---
command:
  - name: fcitx5_switcher
    description: Automatically switch fcitx5 input method status based on window class and title.
---

# fcitx5_switcher

This is a useful tool for CJK input method users.

It can automatically switch fcitx5 input method status based on window class and title.

Example:
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