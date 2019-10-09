#!/bin/bash

_VARS_DEFAULT=({t_so,w_so{,_ice}}{,_new}_b)
_ICOL=11
 
_USAGE="usage: $(basename ${0}) sel file_tmpl vals vars

Args:
    n_sel: Number of lines to be selected. If the number is negative, the lines
        are reversely sorted, which is generally necessary for negative
        deviations. Pass '0' to select all lines.

    op: Operator applied to the selected lines. Choices: 'max', 'min', 'mean',
        'median'.

    title: Title string printed in the top-left cell of the output table.

    file_tmpl: File path template containing '{<val_name>}' which is replaced
        by the values passed as 'vals'. Example: 'cosmo_{ts}.'.

    val_name: Name of values. Must be used as format key in 'file_tmpl'.

    vals: Comma-separated list of values that replace '{<val_name>}' in
        'file_tmpl'.  Each value corresponds to one row in the output table.

    vars (optional): Comma-separated list of variable names. Each is supposed
        to correspond to a column value in the input file and used to select
        input rows by grepping for ' <var> '. Each variable name corresponds
        to one column in the output table.
        Default: ${_VARS_DEFAULT[@]}
"

eval_inargs()
{
    [ ${#} -lt 6 ] && { echo "${_USAGE}" >&2; exit 1; }

    n_sel=${1}
    op=${2}
    title=${3}
    file_tmpl="${4}"
    val_name="${5}"
    vals=(${6//,/ })
    [ ${#} -eq 7 ] && vars=(${7//,/ }) || vars=(${_VARS_DEFAULT[@]})

    # Check file template
    echo "${file_tmpl}" | \grep -q "${val_name}" || {
        echo "invalid file_tmpl '${file_tmpl}': must contain '${val_name}'" >&2
        return 1
    }

    # echo "------------------------------"
    # echo "n_sel     : ${n_sel}"
    # echo "op        : ${op}"
    # echo "title     : ${title}"
    # echo "file_tmpl : ${file_tmpl}"
    # echo "val_name  : ${val_name}"
    # echo "vals (${#vals[@]})  : ${vals[@]}"
    # echo "vars (${#vars[@]})  : ${vars[@]}"
    # echo "------------------------------"
}

main()
{
    setup_env || return 1

    eval_inargs "${@}" || return 1

    table="$(create_table \
        "${n_sel}" "${op}" "${title}" "${file_tmpl}" "${val_name}" \
        "$(pass_arr "${vals[@]}")" "$(pass_arr "${vars[@]}")" \
    )" || return 1

    echo -e "${table}"
}

create_table()
{
    local n_sel="${1}"
    local op="${2}"
    local title="${3}"
    local file_tmpl="${4}"
    local val_name="${5}"
    local vals=($(recv_arr "${6}"))
    local vars=($(recv_arr "${7}"))

    local n0=10
    
    # Determine widths of first column
    local nc0=${#title}
    for val in ${vals[@]}
    do
        [ ${#val} -gt ${nc0} ] && nc0=${#val}
    done
    nc0=$((nc0+3))
    
    # Initialize table
    local table=''

    wcol() { local l=${#1}; echo $((l<n0?n0+3:l+3)); }
    
    # Column names (header row)
    table+="$(\printf "%${nc0}s" "${title}")"
    local var
    for var in ${vars[@]}
    do
        table+="$(\printf "%$(wcol ${var})s" "${var}")"
    done
    table+='\n'
    
    # Iterate over rows
    local val file deviat
    for val in ${vals[@]}
    do
        # Row name ('header column')
        table+="$(\printf "%${nc0}s" ${val})"
    
        # Iterate over columns
        for var in ${vars[@]}
        do
            file=$(echo "${file_tmpl}" | \sed -e 's/{'${val_name}'}/'${val}'/g')
            #[ -f "${file}" ] || { echo "file not found: ${file}" >&2; exit 1; }
            deviat="$(comp_deviat "${var}" "${file}" "${n_sel}" "${op}")"
            table+="$(\printf "%$(wcol ${var})s" "${deviat}")"
        done
        table+='\n'
    done

    echo -e "${table}"
}

comp_deviat()
{
    local var="${1}"
    local file="${2}"
    local n_sel="${3}"
    local op="${4}"

    # Handle missing file
    [ ! -f "${file}" ] && return 0

    # Determine whether to reverse-sort etc.
    local rflag=''
    if [ ${n_sel} -eq 0 ]
    then
        n_sel=$(\cat "${file}" | wc -l)
    elif [ ${n_sel} -lt 0 ]
    then
        rflag='r'
        n_sel=$((-n_sel))
    fi

    # Extract deviations from file
    local deviats=($(
        \cat "${file}" \
        | \grep " ${var} " \
        | \sort -k${_ICOL}n${rflag} \
        | \head -${n_sel} \
        | \sed 's/ \+/ /g' \
        | \cut -d' ' -f${_ICOL}
    ))
    [ ${#deviats} -eq 0 ] && return 0

    # Reduce deviations with the given operator using Python
    #local fmt='{:.f}'
    local fmt='{:.2e}'
    local pycmd="${op}([$(echo "${deviats[*]}" | sed 's/ /,/g')])"
    local result="$(python -c \
        "from numpy import ${op}; print('${fmt}'.format(${pycmd}))")"

    echo "${result}"
}

_SEP='@'
pass_arr() { echo "${@}" | sed "s/ /${_SEP}/g"; }
recv_arr() { echo "${1//${_SEP}/ }"; }

setup_env()
{
    # Load Python module if necessary
    python --version >/dev/null || {
        module load python
        python --version >/dev/null || {
            echo "could not load Python" >&2
            return 1
        }
    }
}

main "${@}"
