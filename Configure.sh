#!/bin/bash

if ! command -v asciinema &> /dev/null
then
    echo "Asciinema is not installed. Installing now..."
    sudo apt update && sudo apt install asciinema -y
else
    echo "Asciinema is already installed."
fi

CURRENT_DIR=$(pwd)
FULL_DIR="${CURRENT_DIR}/static/full"
mkdir -p "${FULL_DIR}"
echo "Recording directory set at ${FULL_DIR}"

ZSHRC="$HOME/.zshrc"
RECORD_CMD="asciinema rec \$FULL_DIR/\$(date +%Y-%m-%d_%H-%M-%S).cast"

if ! grep -q "ASC_REC_ACTIVE" "${ZSHRC}"
then
    echo "Adding asciinema setup to ${ZSHRC}"
    cat <<EOF >> "${ZSHRC}"

# Setup asciinema recording
export FULL_DIR=${FULL_DIR}
trap 'echo Shell exited, stopping recording.; asciinema stop' EXIT
if [ -z "\$ASC_REC_ACTIVE" ]; then
    export ASC_REC_ACTIVE=true
    ${RECORD_CMD}
fi
EOF
fi

echo "Setup complete. Please open a new terminal to start recording sessions."
