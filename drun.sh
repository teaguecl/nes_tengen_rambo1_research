#!/bin/sh
# Run a command in the rambo1-tools container (see Dockerfile). The container is ephemeral (--rm); the repo is mounted at /work.
#
#   ./drun.sh                                   interactive shell in the repo
#   ./drun.sh "cd rom && make"                  quote anything with && | ; > so that it runs inside the container
#   ./drun.sh rom/tools/run_checks.sh           run a script
#   ./drun.sh --device /dev/ttyACM0 python3 -I firmware/rp2350_jig/tools/jig.py --port /dev/ttyACM0 state
#
# Options (before the command):
#   --device DEV    pass a host device (a serial port for the jig/adapter) through, and join the dialout group
#   --rebuild       rebuild the image first (the image is built automatically the first time)
# Environment: DOCKER=podman to use podman, IMAGE=name to use another image name.
# Jig and adapter safety rules: hardware/README.md. Never connect either to a cart that is in a console.
DOCKER=${DOCKER:-docker}
IMAGE=${IMAGE:-rambo1-tools}
cd "$(dirname "$0")" || exit 1
extra=""
rebuild=0
while [ $# -gt 0 ]; do
    case $1 in
        --device)  [ -n "$2" ] || { echo "drun.sh: --device needs a path" >&2; exit 2; }
                   [ -e "$2" ] || { echo "drun.sh: $2 does not exist" >&2; exit 2; }
                   extra="$extra --device $2 --group-add dialout"; shift 2 ;;
        --rebuild) rebuild=1; shift ;;
        --) shift; break ;;
        *) break ;;
    esac
done
if [ "$rebuild" = 1 ] || ! $DOCKER image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "drun.sh: building image $IMAGE ..." >&2
    $DOCKER build -t "$IMAGE" . || exit 1
fi
tty=""
[ -t 0 ] && [ -t 1 ] && tty="-it"
if [ $# -eq 0 ]; then
    # shellcheck disable=SC2086
    exec $DOCKER run --rm $tty $extra -v "$PWD":/work "$IMAGE" bash
fi
# shellcheck disable=SC2086
exec $DOCKER run --rm $tty $extra -v "$PWD":/work "$IMAGE" sh -c "$*"
