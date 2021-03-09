#!/bin/bash

pushd $(pwd)

echo quit | nc -U qemu/monitor.sock

popd
