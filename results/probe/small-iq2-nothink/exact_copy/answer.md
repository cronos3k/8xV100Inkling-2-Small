```yaml
# deployment manifest
version: 7
services:
  gateway:
    image: registry.internal/gateway@sha256:a639d97acc3d9b20c11bf41e15fe48f57bf183f8d1df96ae33777d186f92499c
    port: 9443
    token: efa79df9-32ff-421e-8543-4a854730416e
    timeout: 5
    debug: true
    checksum: d4127d317c1c76be67fceec828e1771e9d07bb9e
  worker:
    image: registry.internal/worker@sha256:3f62e8d73887d92cd2d4f713e6089f6dc5a77f32c875d509ab89861e17441d40
    port: 9100
    token: c728b9da-515f-2332-3cbf-e07b8088cf7d
    timeout: 66
    checksum: 025259a62b8881a38b682768db40bf1823602486
  billing:
    image: registry.internal/billing@sha256:4a60f9ced92a0a4735e538ab866d683ecde917333989fe7e700aa8638f725726
    port: 7001
    token: 2e139c55-f37f-731d-a7ce-f59b5aa7dd9e
    timeout: 8
    retries: 5
    debug: false
    checksum: d1d9ac8ceb4f2845c8280e40dd30c061a9beda2e
  search:
    image: registry.internal/search@sha256:09ee7709d92c6586462ed1d93a2cc13370e5ef87bfbfa9a20d1014ded12e84d6
    port: 9200
    token: ef80f060-6cfd-7119-8535-14cbacad5000
    timeout: 33
    debug: true
    checksum: 4d12322cf83b3dc9faa601929efd66343aa30eb5
  mailer:
    image: registry.internal/mailer@sha256:70cbd19fda7ab5a02a13496654e4160f44b60a6f55580b6764a29387bc2ba91b
    port: 2525
    token: 8bf6395c-fbff-ade5-c4f9-6a7502034f0c
    timeout: 69
    debug: true
    checksum: 2ef9350d82354e04fa40751321e788989c7c659a
```