#!/bin/bash

[ -z "${CHUNK_SIZE}" ] && CHUNK_SIZE=666

declare -a rm_on_exit_items

# Remove all items tagged for removel on exit of script
rm_on_exit()
{
    local item
    for item in "${rm_on_exit_items[@]}"
    do
        rm -rf "${item}"
    done
}

# Tag an item for removal on exit of script
set_rm_on_exit()
{
    local i="${#rm_on_exit_items[@]}"
    [ ${i} -eq 0 ] && trap rm_on_exit EXIT
    for item in "${@}"
    do
        rm_on_exit_items[i]="${item}"
        i=$((i + 1))
    done
}

main()
{
    usage="usage: $(basename ${0}) tag logfile outfile [rows]"
    [ ${#} -lt 3 ] && { echo "${usage}" >&2; return 1; }
   
    # Collect input arguments
    tag="${1}"
    logfile="${2}"
    outfile="${3}"
    shift 3
    rows=(${@})

    echo "----------------------------------------"
    echo "tag     : ${tag}"
    echo "logfile : ${logfile}"
    echo "outfile : ${outfile}"
    echo "rows    : ${rows[@]}"
    echo "----------------------------------------"
    
    # Check validity of rows
    echo "${rows[@]}" | grep -q '^[ 0-9]*$' \
        || { echo "invalid rows: ${rows[@]}" >&2; return 1; }

    # Temporary files for output and chuks of lines
    tmpfile_out=$(mktemp /tmp/ruestefa.extract_tagged_lines.out.XXXXXXXXXXX)
    tmpfile_log=$(mktemp /tmp/ruestefa.extract_tagged_lines.log.XXXXXXXXXXX)
    set_rm_on_exit "${tmpfile_out}" "${tmpfile_log}"
    # echo "temporary files:"
    # echo " * input  : ${tmpfile_log}"
    # echo " * output : ${tmpfile_out}"

    chunk_size="${CHUNK_SIZE}"
    n_lines_tot=$(cat "${logfile}" | wc -l)
    n_chunks=$((n_lines_tot/chunk_size + 1))
    n_lines_check=0
    [ ${n_chunks} -ge 1 ] && echo "processing $(numfmt --grouping ${n_lines_tot}) lines in $(numfmt --grouping ${n_chunks}) chunks of up to $(numfmt --grouping ${chunk_size}) lines"
    for ((i_chunk = 0; i_chunk < n_chunks; i_chunk++))
    do
        line_start=$((i_chunk*chunk_size + 1))
        line_end=$((i_chunk < n_chunks - 1 ? (i_chunk + 1)*chunk_size : n_lines_tot))
        chunk_size_i=$((line_end - line_start + 1))
        pctl=$((100*(i_chunk + 1)/n_chunks))
        [ ${n_chunks} -ge 1 ] && echo -en "\r ${pctl}% | $(numfmt --grouping $((i_chunk + 1)))/$(numfmt --grouping ${n_chunks}) | $(numfmt --grouping ${chunk_size_i}) lines: $(numfmt --grouping ${line_start}) to $(numfmt --grouping ${line_end})"

        # Extract chunk of lines into temporary files
        if [ ${i_chunk} -lt $((n_chunks/2)) ]
        then
            \head -${line_end} "${logfile}" | \tail -${chunk_size_i} > "${tmpfile_log}"
        else
            line_start_up=$((n_lines_tot - line_start + 1))
            \tail -${line_start_up} "${logfile}" | \head -${chunk_size_i} > "${tmpfile_log}"
        fi
        
        # Check than number of lines matches expected chunk size
        n_lines_i=$(cat "${tmpfile_log}" | wc -l)
        if [ ${chunk_size_i} -ne ${n_lines_i} ]
        then
            echo "chunk $((i_chunk + 1))/${n_chunks}: ${chunk_size_i} lines expected, but ${n_lines_i} read" >&2
            return 1
        fi

        # Extract tagged lines (without the tag), optionally select rows
        extract_tagged_lines "${tag}" "${tmpfile_log}" ${rows} >> "${tmpfile_out}" || return ${?}
    done
    echo

    [ -f "${outfile}" ] && \mv -v "${outfile}" "${outfile}.bak"
    \mv "${tmpfile_out}" "${outfile}"

    return 0
}

extract_tagged_lines()
{
    local tag="${1}"
    local logfile="${2}"
    shift 2
    local rows=(${@})
    local lines

    # Extract tagged lines and remove anything before its first occurrence
    # (In cases where a process might have written to an existing line)
    lines="$(cat "${logfile}" | \
        \grep '\(^\|[^a-zA-Z]\)'"${tag}"'[^a-zA-Z]' | \
        perl -pe 's/^.*?'"${tag}"'\b/'"${tag}"'/')"

    # Clean up whitespace and line breaks while removing leading tags
    # (Sometimes multiple parallel processes write on the same line)
    lines="$(echo "${lines//[$'\n\r\n']/ }" | \
        sed -e 's/\t/ /g' \
            -e 's/^ \+//' \
            -e 's/ \+/ /g' \
            -e 's/^\( *'"${tag}"' *\)\+//' \
            -e 's/\( *'"${tag}"' *\)\+$//' \
            -e 's/\( *'"${tag}"' *\)\{2,\}/ '"${tag}"' /' \
            -e 's/ *'"${tag}"' */\n/g' \
    )"

    # Print lines, optionally restricted to certain columns
    if [ "${lines}" != '' ]
    then
        case ${#rows[@]} in
            0) echo -e "${lines}";;
            *) echo -e "${lines}" | cut -d' ' -f$(echo "${rows[@]}" | sed 's/ /,/g');;
        esac
    fi
}

main "${@}"
