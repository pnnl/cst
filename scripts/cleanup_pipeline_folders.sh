#!/bin/bash

PIPELINE_DIR=$(realpath ../..)
DAYS_OLD=30
printf "======== Cleaning up pipeline directories under [%s] older than %s...\n" "$PIPELINE_DIR" "$DAYS_OLD"
find "$PIPELINE_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +$DAYS_OLD -exec rm -rf {} \;
