# Build and analysis tools for the RAMBO-1 project (test ROMs, reference model, RP2350 firmware, sigrok captures, SKiDL netlist).
# Easiest to use through ./drun.sh. Not included: KiCad (use the desktop app), the Arduino IDE/CLI (Mega firmware), and the jig hardware itself.
#
#   docker build -t rambo1-tools .
#   docker run --rm -it -v "$PWD":/work rambo1-tools                          # shell in the repo
#   docker run --rm -v "$PWD":/work rambo1-tools sh -c 'cd rom && make && md5sum build/g*.nes'
#   docker run --rm -v "$PWD":/work rambo1-tools rom/tools/run_checks.sh      # software models only
#   docker run --rm -it --device /dev/ttyACM0 --group-add dialout -v "$PWD":/work rambo1-tools \
#       python3 -I firmware/rp2350_jig/tools/jig.py --port /dev/ttyACM0 state  # talk to the adapter (read docs/hardware.md safety rules first)
FROM ubuntu:24.04

ARG PICO_SDK_VERSION=2.3.1
ENV DEBIAN_FRONTEND=noninteractive

# cc65 2.19 (the version the README's MD5 sums were made with), Python, make, sigrok, and the ARM bare-metal toolchain for the Pico SDK.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential make cmake ninja-build git ca-certificates \
        cc65=2.19-1 python3 python3-venv python3-pip \
        sigrok-cli \
        gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib \
        xxd \
    && rm -rf /var/lib/apt/lists/*

# Pico SDK (only the tinyusb submodule is needed for this firmware).
RUN git clone --depth 1 --branch ${PICO_SDK_VERSION} https://github.com/raspberrypi/pico-sdk /opt/pico-sdk \
    && git -C /opt/pico-sdk submodule update --init --depth 1 lib/tinyusb
ENV PICO_SDK_PATH=/opt/pico-sdk

# SKiDL, to regenerate the cart netlist (hardware/generators/rambo1_cart.py). Everything else in the project uses the standard library.
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir skidl
ENV PATH=/opt/venv/bin:$PATH

# uid 1000 (the image's "ubuntu" user), so files written into the mounted repo belong to a typical desktop user.
USER 1000
WORKDIR /work
CMD ["bash"]
