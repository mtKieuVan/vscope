source $TOOLDIR/env.sh

export PATH="$PATH:$TOOLDIR"

alias ec='vi $TOOLDIR/env.sh'
alias sc='source $TOOLDIR/toolbox.sh'

wp() {

    [ "$1" != "" ] && export WORKSPACE="${WORKDIR}/${1}"

    cd "$WORKSPACE"
}

v() {

    # Search for all files match the keyword (except .git, node_modules, build,…)
    local files
    readarray -d '' files < <(find . -type f \
        -not -path '*/\.git/*' \
        -not -path '*/node_modules/*' \
        -not -path '*/dist/*' \
        -not -path '*/build/*' \
        -iname "*$1*" -print0)

    local count=${#files[@]}

    if [ $count -eq 0 ]; then
        echo "File not found"
        return 1
    elif [ $count -eq 1 ]; then
        vim "${files[0]}"
    else
        echo "Found $count files:"
        local i=1
        for f in "${files[@]}"; do
            echo "[$i] $f"
            ((i++))
        done

        echo -n "Choose file to open: "
        read -r choice

        if [[ $choice =~ ^[0-9]+$ ]] && [ $choice -ge 1 ] && [ $choice -le $count ]; then
            vim "${files[$((choice-1))]}"
        else
            echo "Invalid chosen!"
        fi
    fi
}

