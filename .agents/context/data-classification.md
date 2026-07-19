# Data Classification

| Class | Prompt | Logs | External tools | Example |
|---|---:|---:|---:|---|
| Public | yes | yes | allowlisted | published docs |
| Internal | scoped | redacted | approved only | source code |
| Confidential | no by default | no | no | customer/business data |
| Restricted | never | never | never | credentials/regulated data |

Replace this with organizational policy and enforce it outside the model through identity, DLP, runtime,
and logging configuration.
