# Permission-controlled data policy

The external observational endpoint is outside the public reproduction boundary. Public materials may contain only aggregate metrics, a non-identifying design manifest, a synthetic schema and a permission statement.

Never add:

- provider or site identifiers;
- named locations or coordinates;
- hourly observation or prediction records;
- matched row-level evaluation tables;
- point contracts;
- representative external time-series source data or its real generator;
- private data paths or credentials.

The Supplementary figure titled “Representative external venue time-series comparisons” remains outside this repository. Its artwork, row-level source data and real generator are not included.

The public interface in `src/wce/external_interface/` validates only a synthetic schema. Execution against real observations requires a separate permission-controlled environment and is not part of public CI.

