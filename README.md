# io-opsworks sample script

A test python script to work with AWS implemented as a testing case.

## Getting Started

Configure AWS profile, clone repo, update hardcoded VPC, region and desired token save path. Then run with python.

Script is intended to run without parameters locally and execute itself with "start" parameter when uploaded to server.

### Prerequisites

Described in requirements.txt

### Known issues

mkfs commands cannot run through SSH session invoked by paramiko library.

