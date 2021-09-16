## Using kubectl helpers

The `kubectl_helpers` directory contains a series of helper bash scripts designed to make accessing kubernetes 
resources a bit easier. Most of these scripts take in 2 arguments:

- `DEPLOYMENT_TARGET` specifies which deployment environment to work against. It must match the current set context (see below). Valid options are `prod` and `dev`
- `COMPONENT` specifies which of seqr's kubernetes components to access - valid options include `seqr`, `elasticsearch`, and `redis`

Before running these scripts, you need to set the kubernetes context to the desired deployment target via the 
`set_env.sh` script. For example, to view the logs for elasticsearch in dev you would run the following

```bash
./kubectl_helpers/set_env.sh dev
./kubectl_helpers/logs.sh dev elasticsearch
```
 