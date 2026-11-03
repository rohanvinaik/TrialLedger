# Restore the complete retained packet

The adjacent `registry-run.tar.gz` contains the original complete packet, including raw evidence, exact requests/results and writing-version manifests. Every archive member was read back and its SHA-256 matched the original bytes before loose generated files were removed. No source values or observations were changed.

From the repository root:

```sh
tar -xzf openspec/changes/integrate-warranted-design-session/evidence/registry-run.tar.gz -C openspec/changes/integrate-warranted-design-session/evidence
```

This restores the original paths and README. Then follow the original replay instructions under their writing version. Extraction restores preserved artifacts; `verify` does not regenerate missing artifacts. Historical results retain their writing version.
