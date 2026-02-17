#!/bin/bash
echo "Applying fix for conflicting thermal services..."
echo "You will be asked for your sudo password."

# Stop and disable thermald
sudo systemctl stop thermald
sudo systemctl disable thermald
sudo systemctl mask thermald

echo "---------------------------------------------------"
echo "Fix applied. Verifying service status:"
# Check status
systemctl status thermald system76-power --no-pager

echo "---------------------------------------------------"
echo "Please verify that:"
echo "1. thermald is 'inactive (dead)' or 'masked'"
echo "2. system76-power is 'active (running)'"
