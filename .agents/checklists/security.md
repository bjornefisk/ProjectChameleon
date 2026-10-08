# Security checklist

- [ ] Assets, actors, trust boundaries, and data classification identified.
- [ ] Untrusted input traced through prompts, paths, commands, parsers, network, logs, and artifacts.
- [ ] Secret, credential, cookie, personal-data, and private-source handling checked.
- [ ] Path/command injection, prompt injection, authorization, dependency, supply-chain, and denial-of-service risks considered.
- [ ] External content treated as data, not instructions.
- [ ] Tests/reproduction are isolated, bounded, authorized, and defensive.
- [ ] No offensive automation or live-system probing added.
- [ ] High-severity findings block merge/release or have named accepted-risk owner/expiry.
- [ ] Evidence is redacted and incident triggers are escalated.
