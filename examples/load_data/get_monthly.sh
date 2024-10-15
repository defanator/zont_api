#!/bin/bash -x

TARGET_DIR="${HOME}/home-net/baxi-connect"

# ./export_timeseries.py --from=2023-07-01 --to=2023-08-01 --verbose --targetdir=${HOME}/home-net/baxi-connect/2023-07 >${HOME}/home-net/baxi-connect/2023-07/export.out 2>&1

START_YEAR=2023
START_MONTH=11
END_YEAR=2024
END_MONTH=9

YEAR=${START_YEAR}
MONTH=${START_MONTH}

while true; do
    printf -v DATESTR_FROM "%04d-%02d-01" "${YEAR}" "${MONTH}"
    printf -v TARGET_SUBDIR "%04d-%02d" "${YEAR}" "${MONTH}"

    MONTH=$((MONTH + 1))
    if ((MONTH > 12)); then
        MONTH=1
        YEAR=$((YEAR + 1))
    fi

    printf -v DATESTR_TO "%04d-%02d-01" "${YEAR}" "$((MONTH))"

    mkdir -p "${TARGET_DIR}/${TARGET_SUBDIR}"
    ./export_timeseries.py --from="${DATESTR_FROM}" --to="${DATESTR_TO}" --targetdir="${TARGET_DIR}/${TARGET_SUBDIR}" >"${TARGET_DIR}/${TARGET_SUBDIR}/export.out" 2>&1

    if ((MONTH > END_MONTH)) && ((YEAR >= END_YEAR)); then
        break
    fi

    echo "Press any key to continue or Ctrl+C to exit..." >&2
    read -r
done
