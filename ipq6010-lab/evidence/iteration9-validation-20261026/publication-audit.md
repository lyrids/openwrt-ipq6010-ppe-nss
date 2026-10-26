# Publication checks

Known historical Wi-Fi test keys and the current runtime key were compared against candidate staged text locally on the DUT; only a pass/fail result left it. No live key was extracted to Orb for scanning. No matches found. Credential-bearing router/client config backups stayed on their devices and are excluded from this archive.

All staged files were also checked on Orb for private-key blocks, GitHub/AWS token patterns, credentialed URLs and forbidden image/archive binaries. Build/rootfs firmware binaries remain outside Git. Raw command logs retain original whitespace; source/script formatting checked separately. Bash syntax checks, existing three mocked NSS regression harnesses, live AP lifecycle assertion, new-image RAM boot, short Wi-Fi qualifications and both thirty-minute soaks completed. Hardware limitations and unresolved endpoint UDP under-delivery are retained in the reports.
