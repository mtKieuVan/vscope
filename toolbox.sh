source $TOOLDIR/env.sh

export PATH="$PATH:$TOOLDIR"

alias ec='vi $TOOLDIR/env.sh'
alias sc='source $TOOLDIR/toolbox.sh'

wp() {

    [ "$1" == "-l" ] && ls ${WORKDIR} && return

    [ "$1" != "" ] && export WORKSPACE="${WORKDIR}/${1}"

    cd "$WORKSPACE"
}

v() {

    local keyword="$1"
    local line_number

    # Check if the input contains a colon and a number, like <filename>:<line number>
    if [[ "$keyword" =~ ^(.*):([0-9]+)$ ]]; then
        keyword="${BASH_REMATCH[1]}"
        line_number="${BASH_REMATCH[2]}"
    fi

    # If the keyword is a path that exists, open it directly.
    if [ -e "$keyword" ]; then
        if [ -n "$line_number" ]; then
            vim "+$line_number" "$keyword"
        else
            vim "$keyword"
        fi
        return 0
    fi

    # Search for all files match the keyword (except .git, node_modules, build,…)
    local files
    readarray -d '' files < <(find . -type f \
        -not -path '*/\.git/*' \
        -not -path '*/node_modules/*' \
        -not -path '*/dist/*' \
        -not -path '*/build/*' \
        -iname "*$keyword*" -print0)

    local count=${#files[@]}

    if [ $count -eq 0 ]; then
        echo "File not found"
        return 1
    fi

    local file_to_open
    if [ $count -eq 1 ]; then
        file_to_open="${files[0]}"
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
            file_to_open="${files[$((choice-1))]}"
        else
            echo "Invalid chosen!"
            return 1
        fi
    fi

    if [ -n "$line_number" ]; then
        vim "+$line_number" "$file_to_open"
    else
        vim "$file_to_open"
    fi
}

f() {
    grep -nHE '^[^[:space:]\t].*[^;]$|^}'  *  | grep -vP "\d+:#" | grep -vP "\d+:/\*" | grep -A 1 $1
}

