# bash completion script for pypr

_pypr() {
    local commands=("dumpjson" "edit" "help" "version" "reload" "gbar" "menu" "toggle_special" "attach" "hide" "show" "toggle" "layout_center" "attract_lost" "relayout" "shift_monitors" "toggle_dpms" "zoom" "expose" "change_workspace" "wall" "fetch_client_menu" "unfetch_client")

    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "$prev" in
        layout_center)
            COMPREPLY=($(compgen -W "next prev clear" -- "$cur"))
            return 0
            ;;
        zoom)
            COMPREPLY=($(compgen -W "+1 -1 ++1 --1 ++0.5 --0.5" -- "$cur"))
            return 0
            ;;
        shift_monitors|change_workspace)
            COMPREPLY=($(compgen -W "+1 -1" -- "$cur"))
            return 0
            ;;
        wall)
            COMPREPLY=($(compgen -W "clear next" -- "$cur"))
            return 0
            ;;
        gbar)
            COMPREPLY=($(compgen -W "restart" -- "$cur"))
            return 0
            ;;
        --debug|wall|toggle_special|toggle_dpms|expose|fetch_client_menu|unfetch_client|relayout|toggle|show|hide|attach|toggle_special|menu|reload|version|help|edit|dumpjson)
            ;;
        *)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--debug" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "${commands[*]}" -- "$cur"))
            fi
            return 0
            ;;
    esac
}

complete -F _pypr pypr
